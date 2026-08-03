# httpstat

> A command-line tool that presents curl timing statistics in a readable form.

## Overview

httpstat wraps curl and displays DNS, TCP, TLS, server-processing, and transfer
timings. Upstream ships the tool as a single Python 3 script with no third-party
Python module dependencies.

## OHOS Adaptation

- Packages `httpstat.py` as the `bin/httpstat` command.
- Rewrites the upstream generic Python shebang to `/usr/bin/env python3`.
- Uses offline consumer tests for CLI validation and a full loopback HTTP request.
- Preserves the upstream curl path and falls back to Python's HTTP stack when curl is absent.

## Dependencies

| Dependency | Type | Purpose |
|---|---|---|
| Python 3 | Runtime | Executes the packaged script |
| Python 3 standard library | Runtime fallback | Performs basic HTTP/HTTPS requests when curl is unavailable |

Curl-specific extra options require an installed curl command.

## Functional Verification

```sh
httpstat --version
httpstat --help
httpstat https://example.com
```

## References

- [Source repository](https://github.com/reorx/httpstat)
- [Homebrew formula](https://formulae.brew.sh/formula/httpstat)
