# libkcapi

## Description
Linux Kernel Crypto API User Space Interface Library

libkcapi provides a user-space interface to the Linux Kernel Crypto API. It enables applications to use kernel cryptographic algorithms without needing to implement them in user space, providing better performance and security.

## Features
- Hash algorithms (SHA, MD5, etc.)
- Symmetric cipher operations (AES, DES, etc.)
- AEAD cipher operations (AES-GCM, AES-CCM, etc.)
- Random number generation
- Key derivation functions
- Digital signature operations

## Version Information
- Latest compiled version: 1.5.0
- Release date: 2024-01-11

## Build System
- Type: autotools
- Requires: autoconf, automake, libtool

## Dependencies
- None (uses kernel crypto API directly)

## Compiled Versions
- [1.5.0](./1.5.0/) - 2026-06-10

## Notes
- Requires autoreconf -i to generate configure script from configure.ac
- Needs patch for OHOS platform due to sockaddr_storage redefinition issue
- Compiler flag -Wno-sign-compare required to suppress CMSG_NXTHDR warning