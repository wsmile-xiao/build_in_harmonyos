# cvsync

CVS repository synchronization utility.

## Description

cvsync is a portable CVS repository synchronization utility that allows users to mirror CVS repositories. It provides both client (cvsync) and server (cvsyncd) components.

## Components

- **cvsync**: CVS repository client synchronization tool
- **cvsyncd**: CVS repository server daemon
- **cvscan**: Scan RCS files for metadata
- **rcscan**: RCS file scanner
- **rcscmp**: RCS file comparison tool
- **cvsup2cvsync**: Convert CVSup configuration to cvsync
- **cvsync2cvsup**: Convert cvsync configuration to CVSup

## Versions

- **0.24.19**: Latest stable version (2026-06-12)

## Dependencies

- OpenSSL (libcrypto)
- zlib

## Build Notes

cvsync uses BSD Makefile build system without configure script. Must specify HASH_TYPE=openssl or libgcrypt for hash functions.

## License

BSD License

## Homepage

- GitHub: https://github.com/cvsync/cvsync