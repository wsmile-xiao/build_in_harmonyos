# testssl.sh

TLS/SSL security testing tool for checking server's TLS/SSL ciphers, protocols and cryptographic flaws.

## Version
- 3.2.3 (bugfix release)

## Description
testssl.sh is a free command line tool which checks a server's service on any port for:
- TLS/SSL cipher support
- Protocol versions
- Cryptographic flaws
- Recent vulnerabilities

## Key Features
- Clear output format
- Machine readable output (CSV, JSON, HTML)
- No installation required - works out of the box
- Works on Linux, MacOS, FreeBSD, NetBSD, WSL2, MSYS2/Cygwin, OpenBSD

## Dependencies
- bash >= 3.2
- OpenSSL (system or bundled)
- Standard Unix tools (sed, awk, grep)

## Installation
Simply copy the files to the target directory:
```
./install.sh
```

## Usage
```bash
testssl.sh --help
testssl.sh https://example.com
testssl.sh example.com:443
```

## License
GPL-2.0

## Homepage
https://testssl.sh