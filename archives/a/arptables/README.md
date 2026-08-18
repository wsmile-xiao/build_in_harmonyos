# arptables

arptables is a userspace ARP packet filtering tool for Linux. It provides
command-line management of ARP table rules, similar to iptables but for
ARP packets.

## Versions

| Version | Status | Notes |
|---------|--------|-------|
| 0.0.4 | built | Adapted for HarmonyOS (musl libc, OHOS SDK) |

## Description

arptables allows administrators to configure ARP packet filtering rules
in the Linux kernel's ARP table. It supports:

- Filter rules based on source/target IP, MAC addresses, ARP operation
- Standard targets: ACCEPT, DROP, RETURN
- Extension targets: CLASSIFY, mangle
- Rule save/restore functionality

## Build System

- Type: Makefile (plain make, no autotools/CMake)
- Compiler: clang
- Dependencies: None (only libc)

## Links

- [GitHub Repository](https://github.com/KVM-COLO/arptables)
