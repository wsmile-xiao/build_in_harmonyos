# swtpm 0.10.1 - OHOS Pre-compiled Package

## Description
swtpm is a TPM (Trusted Platform Module) emulator based on libtpms.
It provides a software TPM for virtual machines and testing environments.

## Binaries
- swtpm: TPM emulator daemon
- swtpm_bios: BIOS tool for TPM initialization
- swtpm_ioctl: TPM control interface tool
- swtpm_localca: Local CA management tool
- swtpm_setup: TPM setup tool

## Build Configuration
- System: autotools
- Compiler: clang 15.0.4
- Options: --without-gnutls --without-seccomp --without-cuse --disable-tests --disable-hardening

## Dependencies
- libtpms 0.10.0
- glib 2.88.0
- json-glib 1.6.6
- libtasn1 4.21.0
- openssl 3.5.6
