# mokutil

## What is it?

mokutil is a tool for managing Machine Owner Keys (MOK) on UEFI Secure Boot systems. It allows users to enroll, delete, and list MOK keys used to verify signed kernel modules and binaries.

## Key Features

- MOK key enrollment and management
- Secure Boot key verification
- Password-based key protection

## OHOS/HarmonyOS Adaptation

- **Build type**: autotools
- **5 patches required**:
  - Remove `-fshort-wchar` flag (conflicts with musl wchar_t)
  - Add musl_shim.c/h for `l64a()` and `getspnam()` compatibility
  - Modify mokutil.c to use musl_shim header
  - Add musl_shim to Makefile.am SOURCES
- **Dependencies**: openssl/3.5.6, efivar/39, libkeyutils/1.6.3

## Version 0.7.2

- Status: published
- Build date: 2026-06-09
- 5 patches applied for musl libc compatibility