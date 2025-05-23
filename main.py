import argparse
import os
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
    parser = argparse.ArgumentParser(description="Find near-duplicate files using SimHash.")
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
    Finds near-duplicate files within a given directory using ssdeep.

    Args:
        directory (str): The directory to scan.
        threshold (int): The similarity threshold (0-100).
        min_size (int): The minimum file size to consider.

    Returns:
        dict: A dictionary where keys are representative files and values are lists of similar files.
             Returns an empty dictionary if no similar files are found or an error occurs.
    """
    file_hashes = {}
    clusters = {}

    if not os.path.isdir(directory):
        logging.error(f"Invalid directory: {directory}")
        return {}

    try:
        for root, _, files in os.walk(directory):
            for filename in files:
                filepath = os.path.join(root, filename)
                if os.path.getsize(filepath) < min_size:
                    logging.debug(f"Skipping {filepath} due to small size.")
                    continue

                ssdeep_hash, xxhash_hash = calculate_hashes(filepath)
                if ssdeep_hash and xxhash_hash:
                    file_hashes[filepath] = (ssdeep_hash, xxhash_hash)
    except OSError as e:
        logging.error(f"OS error during file traversal: {e}")
        return {}
    except Exception as e:
        logging.error(f"Unexpected error during file processing: {e}")
        return {}

    # Cluster files based on ssdeep similarity
    for filepath1, (ssdeep_hash1, _) in file_hashes.items():
        if filepath1 in clusters:
            continue  # Already part of a cluster

        cluster = [filepath1]
        for filepath2, (ssdeep_hash2, _) in file_hashes.items():
            if filepath1 != filepath2 and filepath2 not in clusters:
                try:
                    similarity = ssdeep.compare(ssdeep_hash1, ssdeep_hash2)
                    if similarity >= threshold:
                        cluster.append(filepath2)
                        clusters[filepath2] = True # mark that file2 is already in the cluster
                except ssdeep.error as e:
                    logging.warning(f"ssdeep comparison error between {filepath1} and {filepath2}: {e}")
                except Exception as e:
                    logging.error(f"Unexpected comparison error between {filepath1} and {filepath2}: {e}")
        if len(cluster) > 1:
            yield filepath1, cluster


def main():
    """
    Main function to execute the SimHash-based duplicate file finder.
    """
    args = setup_argparse()

    # Set log level based on command-line argument
    logging.getLogger().setLevel(args.log_level)

    logging.info(f"Starting SimHash deduplication in directory: {args.directory}")

    try:
        for representative, cluster in find_similar_files(args.directory, args.threshold, args.min_size):
            print(f"Cluster representative: {representative}")
            for file in cluster:
                print(f"  - {file}")
            print("-" * 20)

    except Exception as e:
        logging.critical(f"An unhandled exception occurred: {e}")
        exit(1)

    logging.info("SimHash deduplication complete.")


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