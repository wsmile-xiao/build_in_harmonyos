# macifrename

macifrename is a small command-line tool that renames network interfaces
according to configured MAC addresses, so interface names can remain stable
across boots.

## Adapted versions

| Version | Status | Conan reference |
|---------|--------|-----------------|
| 0.1.2 | built | `macifrename/0.1.2` |

## OHOS adaptation

- Uses `<net/if.h>` instead of `<linux/if.h>` to avoid duplicate
  `sockaddr_storage` definitions with OHOS target headers.
- Defines `_GNU_SOURCE` so `struct ifreq` remains visible with the target
  headers.
- Consumer tests validate safe command behavior only. Real network interface
  renaming is intentionally not executed because it mutates system networking.

## Upstream

- Homepage: https://git.sr.ht/~kaniini/macifrename
- Source: https://git.sr.ht/~kaniini/macifrename/archive/0.1.2.tar.gz
- License: ISC
