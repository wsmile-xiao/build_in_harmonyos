# cntlm

cntlm is an NTLM/NTLMv2 authenticating HTTP proxy with TCP/IP tunneling support.

## Features

- NTLM, NTLM Session Response and NTLMv2 authentication against corporate proxies
- Standalone proxy mode, parent-proxy forwarding, SOCKS5 gateway and TCP tunnels
- Password hashing with `cntlm -H`, interactive password support, PAC file support
- Bundled duktape engine for PAC handling, optional Kerberos via GSS

## OHOS adaptation

- Build system is a plain `Makefile` plus a custom `configure` shell probe script.
- Recipe pre-runs `sh ./configure` with Conan-provided `CC`, then `make -j1`.
- Package installs only the `cntlm` binary, man page and sample config.
- No upstream test suite exists, so `test_package` executes the built binary.

## Dependencies

- No external library dependencies (Kerberos auto-disabled without GSS).

## References

- https://github.com/versat/cntlm
- http://cntlm.sourceforge.net/
