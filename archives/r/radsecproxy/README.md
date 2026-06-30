# RadSecProxy

RADSEC (RADIUS over TLS/TCP/DTLS) proxy server for secure RADIUS communication.

## Overview

RadSecProxy is a proxy that can convert between different RADIUS transport protocols:
- UDP RADIUS (traditional)
- TCP RADIUS
- TLS (RadSec)
- DTLS

## OHOS Adaptation Notes

### Platform Compatibility Issues

1. **DNS SRV/NAPTR Lookup Disabled**: musl libc does not provide `res_nquery` and `_res` global variable, so DNS SRV/NAPTR dynamic discovery is disabled. This does not affect basic RADIUS proxy functionality.

2. **mallopt M_TRIM_THRESHOLD**: musl libc provides `mallopt` stub but does not support `M_TRIM_THRESHOLD` constant. Fixed with conditional compilation.

3. **HMDFS setgid Permission**: musl `mktemp -d` creates temp directories with setgid permission inheritance, causing write failures. Fixed by using pre-defined temp directory.

## Dependencies

- openssl 1.1.1w
- nettle 3.10

## Features Supported

- ✓ UDP RADIUS
- ✓ TCP RADIUS
- ✓ TLS (RadSec)
- ✓ DTLS
- ✗ DNS SRV/NAPTR dynamic discovery (musl libc limitation)

## Installation

```bash
tar xzf radsecproxy-1.11.2-aarch64-ohos.tar.gz -C /usr/local
export LD_LIBRARY_PATH=/usr/local/lib:$LD_LIBRARY_PATH
/usr/local/sbin/radsecproxy -v
```

## Configuration

See `/usr/local/etc/radsecproxy.conf-example` for example configuration.

## Version History

| Version | Status | Date | Notes |
|---------|--------|------|-------|
| 1.11.2 | published | 2026-05-21 | First successful build |

## License

BSD-2-Clause