# keystone

Keystone is a lightweight multi-platform, multi-architecture assembler framework based on LLVM.

## Description

Keystone offers unparalleled features:

- Multi-architecture, with support for Arm, Arm64 (AArch64/Armv8), Ethereum Virtual Machine, Hexagon, Mips, PowerPC, Sparc, SystemZ & X86 (include 16/32/64bit).
- Clean/simple/lightweight/intuitive architecture-neutral API.
- Implemented in C/C++ languages, with bindings for Java, Masm, C#, PowerShell, Perl, Python, NodeJS, Ruby, Go, Rust, Haskell, VB6 & OCaml available.
- Native support for Windows & *nix (with Mac OSX, Linux, *BSD & Solaris confirmed).
- Thread-safe by design.
- Open source - with a dual license.

## Information

- Homepage: https://github.com/keystone-engine/keystone
- License: GPL-2.0-only
- Build system: CMake (vendored LLVM)
- Category: dev

## OpenHarmony Adaptation

- Key points:
  - Vendored LLVM uses common symbols requiring `-fcommon` on clang 15+
  - `CMAKE_POLICY_VERSION_MINIMUM=3.5` for old `cmake_minimum_required(VERSION 2.8.7)`
  - No external dependencies (LLVM is vendored)
  - Produces both library (libkeystone) and executable (kstool)
