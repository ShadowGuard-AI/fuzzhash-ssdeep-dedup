# fuzzhash-SimHashDedup
Command-line utility that uses SimHash to find near-duplicate files within a given directory, reporting on identified clusters of similar files. - Focused on Calculates fuzzy hashes (e.g., ssdeep) and strong hashes (e.g., xxhash) of files and directories to identify similar files, even with slight variations. Useful for malware analysis, code reuse detection, and identifying near-duplicate data. Provides command-line and API access for integration with other security tools.

## Install
`git clone https://github.com/ShadowStrikeHQ/fuzzhash-simhashdedup`

## Usage
`./fuzzhash-simhashdedup [params]`

## Parameters
- `-h`: Show help message and exit
- `--threshold`: No description provided
- `--log-level`: No description provided
- `--min-size`: No description provided

## License
Copyright (c) ShadowStrikeHQ
