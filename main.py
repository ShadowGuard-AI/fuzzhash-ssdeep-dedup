import argparse
import os
import sys
import hashlib
import logging
import ssdeep
import xxhash

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def setup_argparse():
    """
    Sets up the argument parser for the command-line interface.
    """
    parser = argparse.ArgumentParser(description="Find near-duplicate files using ssdeep fuzzy hashing, with xxhash used as an exact match check.")
    parser.add_argument("directory", help="The directory to scan for files.")
    parser.add_argument("--threshold", type=int, default=70,
                        help="Similarity threshold (0-100).  Higher values mean more similar files are grouped. Default: 70")
    parser.add_argument("--log-level", choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'], default='INFO',
                        help="Set the logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL). Default: INFO")
    parser.add_argument("--min-size", type=int, default=1024,
                        help="Minimum file size (in bytes) to consider. Default: 1024")
    return parser.parse_args()


def calculate_hashes(filepath):
    """
    Calculates fuzzy hash (ssdeep) and strong hash (xxhash) for a given file.

    Args:
        filepath (str): The path to the file.

    Returns:
        tuple: A tuple containing the ssdeep hash and the xxhash.
               Returns (None, None) if an error occurs.
    """
    try:
        with open(filepath, "rb") as f:
            file_content = f.read()

        ssdeep_hash = ssdeep.hash(file_content)
        xxhash_hash = xxhash.xxh64(file_content).hexdigest()

        return ssdeep_hash, xxhash_hash
    except FileNotFoundError:
        logging.error(f"File not found: {filepath}")
        return None, None
    except PermissionError:
        logging.error(f"Permission error accessing: {filepath}")
        return None, None
    except Exception as e:
        logging.error(f"Error calculating hashes for {filepath}: {e}")
        return None, None


def find_similar_files(directory, threshold, min_size):
    """
    Finds near-duplicate files within a given directory using ssdeep fuzzy
    hashing, with the xxhash value used as an exact match check.

    Args:
        directory (str): The directory to scan.
        threshold (int): The similarity threshold (0-100).
        min_size (int): The minimum file size to consider.

    Returns:
        tuple or None: None when the directory argument is not a directory.
        Otherwise a tuple (clusters, counts), where clusters is a list of
        (representative, member list) pairs for groups of more than one file,
        and counts is a dict with the number of files seen, skipped, and
        hashed. Clusters are connected groups: files linked by a chain of
        matches belong to one cluster even when the ends of the chain do not
        match each other directly.
    """
    file_hashes = {}
    counts = {"seen": 0, "skipped": 0, "hashed": 0}

    if not os.path.isdir(directory):
        logging.error(f"Invalid directory: {directory}")
        return None

    try:
        for root, _, files in os.walk(directory):
            for filename in files:
                filepath = os.path.join(root, filename)
                counts["seen"] += 1
                if os.path.getsize(filepath) < min_size:
                    counts["skipped"] += 1
                    logging.debug(f"Skipping {filepath} due to small size.")
                    continue

                ssdeep_hash, xxhash_hash = calculate_hashes(filepath)
                if ssdeep_hash and xxhash_hash:
                    file_hashes[filepath] = (ssdeep_hash, xxhash_hash)
                    counts["hashed"] += 1
                else:
                    counts["skipped"] += 1
    except OSError as e:
        logging.error(f"OS error during file traversal: {e}")
        return [], counts
    except Exception as e:
        logging.error(f"Unexpected error during file processing: {e}")
        return [], counts

    # Union-find over the hashed files, so clusters are connected groups.
    parent = {filepath: filepath for filepath in file_hashes}

    def find(path):
        while parent[path] != path:
            parent[path] = parent[parent[path]]
            path = parent[path]
        return path

    def union(path_a, path_b):
        root_a, root_b = find(path_a), find(path_b)
        if root_a != root_b:
            parent[root_b] = root_a

    # Exact match pass: files with equal xxhash values are exact duplicates.
    by_xxhash = {}
    for filepath, (_, xxhash_hash) in file_hashes.items():
        by_xxhash.setdefault(xxhash_hash, []).append(filepath)
    for group in by_xxhash.values():
        for other in group[1:]:
            union(group[0], other)

    # ssdeep pass: link every pair that meets the similarity threshold.
    filepaths = list(file_hashes)
    for i, filepath1 in enumerate(filepaths):
        ssdeep_hash1 = file_hashes[filepath1][0]
        for filepath2 in filepaths[i + 1:]:
            ssdeep_hash2 = file_hashes[filepath2][0]
            try:
                similarity = ssdeep.compare(ssdeep_hash1, ssdeep_hash2)
                if similarity >= threshold:
                    union(filepath1, filepath2)
            except ssdeep.error as e:
                logging.warning(f"ssdeep comparison error between {filepath1} and {filepath2}: {e}")
            except Exception as e:
                logging.error(f"Unexpected comparison error between {filepath1} and {filepath2}: {e}")

    groups = {}
    for filepath in filepaths:
        groups.setdefault(find(filepath), []).append(filepath)

    clusters = [(members[0], members) for members in groups.values() if len(members) > 1]
    return clusters, counts


def main():
    """
    Main function to execute the ssdeep fuzzy hash duplicate file finder.
    """
    args = setup_argparse()

    # Set log level based on command-line argument
    logging.getLogger().setLevel(args.log_level)

    logging.info(f"Starting ssdeep fuzzy hash deduplication in directory: {args.directory}")

    try:
        result = find_similar_files(args.directory, args.threshold, args.min_size)
    except Exception as e:
        logging.critical(f"An unhandled exception occurred: {e}")
        sys.exit(1)

    if result is None:
        logging.error(f"Cannot deduplicate: '{args.directory}' is not a directory.")
        sys.exit(1)

    clusters, counts = result
    logging.info(f"Files seen: {counts['seen']}, skipped: {counts['skipped']}, hashed: {counts['hashed']}")

    if counts["hashed"] == 0:
        logging.error("No files were hashed, so no deduplication was performed.")
        sys.exit(1)

    for representative, cluster in clusters:
        print(f"Cluster representative: {representative}")
        for file in cluster:
            print(f"  - {file}")
        print("-" * 20)

    logging.info("ssdeep fuzzy hash deduplication complete.")


if __name__ == "__main__":
    main()

# Example Usage (assuming you have two nearly identical files in /tmp/test_dir):
# 1. Create a test directory and files:
#    mkdir /tmp/test_dir
#    echo "This is a test file." > /tmp/test_dir/file1.txt
#    echo "This is a test file." > /tmp/test_dir/file2.txt
#    echo "This is slightly different test file." >> /tmp/test_dir/file2.txt
# 2. Run the script:
#    python your_script_name.py /tmp/test_dir
# 3. Observe the output, which should identify file1.txt and file2.txt as a cluster.
#    You can also adjust the threshold and min-size parameters:
#    python your_script_name.py /tmp/test_dir --threshold 60 --min-size 10