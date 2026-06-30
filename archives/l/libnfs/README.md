# libnfs

NFS client library - libnfs is a client library for accessing NFS shares over a network.

## Description

libnfs provides a client-side implementation of the NFS protocol, allowing applications to:
- Mount NFS shares
- Read and write files on remote NFS servers
- Perform file operations (stat, chmod, chown, etc.)
- Support NFSv3 and NFSv4 protocols

## Versions

| Version | Status | Build Date | Notes |
|---------|--------|------------|-------|
| 6.0.2 | published | 2026-05-20 | CMake build, no patches required |

## Dependencies

- **Build**: No build dependencies (only requires libc)
- **Runtime**: libc

## Build System

libnfs supports both CMake and Autotools build systems. For HarmonyOS, CMake is the recommended build method.

## Usage

After installation via cmd-pkgs, the library can be used with:

```c
#include <nfsc/libnfs.h>

struct nfs_context *nfs = nfs_init_context();
// Use NFS API functions...
nfs_destroy_context(nfs);
```

Link with: `-lnfs`

## References

- Official repository: https://github.com/sahlberg/libnfs
- Documentation: See header files in `include/nfsc/`