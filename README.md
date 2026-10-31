![Banner](banner.png)

# fuzzhash-ssdeep-dedup
Command-line utility that uses ssdeep fuzzy hashing to find near-duplicate files within a given directory, reporting on identified clusters of similar files. Files with an equal xxhash value are grouped as exact duplicates first, and ssdeep similarity then links near duplicates into connected clusters. - Focused on Calculates fuzzy hashes (e.g., ssdeep) and strong hashes (e.g., xxhash) of files and directories to identify similar files, even with slight variations. Useful for malware analysis, code reuse detection, and identifying near-duplicate data. Provides command-line and API access for integration with other security tools. Every run logs the counts of files seen, skipped, and hashed; a run that hashes no files, and a scan target that is not a directory, exit 1 without a completion claim.

## Install
`git clone https://github.com/ShadowStrikeHQ/fuzzhash-ssdeep-dedup`

## Usage
`./fuzzhash-ssdeep-dedup [params]`

## Parameters
- `-h`: Show help message and exit
- `--threshold`: No description provided
- `--log-level`: No description provided
- `--min-size`: No description provided

## License
Copyright (c) ShadowStrikeHQ
