# oas

`oas` (Output Address Selection) is a small shared library that wraps the
`connect()` syscall so an application's outgoing TCP connections can be steered
to a chosen IPv6 source address from a rule list (RFC 6724 style policy, applied
earlier than the kernel routing decision).

## Versions

| Version | Status |
| --- | --- |
| 0.0.20220224 | built |

Homepage: https://github.com/ThomasNoll/oas
