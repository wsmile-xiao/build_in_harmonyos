# Masscan

Masscan is the fastest internet port scanner. It can scan the entire internet in under 6 minutes, transmitting 10 million packets per second from a single machine.

## Features

- Asynchronous TCP/IP stack for high-speed port scanning
- Built-in service banner grabbing
- JSON, XML, binary, and text output formats
- Custom TCP/IP stack (does not use host networking stack)

## OHOS Adaptation

### Key Issues

1. **sockaddr_storage redefinition**: Linux kernel headers and OHOS system headers both define `sockaddr_storage`, causing conflicts. Fixed by defining `_UAPI_LINUX_SOCKET_H` to prevent inclusion of conflicting kernel headers.

2. **GNU extension functions**: `getservbyport_r` and `pthread_setaffinity_np` are GNU extensions not available on OHOS. Added `__OHOS__` condition guards to skip these code paths.

3. **Install command**: The Makefile uses the `install` command which is not available on OHOS. Replaced with `mkdir -p` and `cp`.

## Dependencies

- No external library dependencies (only requires a C compiler)
- Runtime: may need root privileges for raw socket access

## References

- GitHub: https://github.com/robertdavidgraham/masscan
- License: AGPL-3.0
