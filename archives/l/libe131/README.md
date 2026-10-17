# libe131

libe131 is a lightweight C/C++ library for the E1.31 (sACN) protocol,
used to transport DMX lighting universes over UDP (unicast/multicast).

## OHOS adaptation

- Builds the official v1.4.0 release tarball with its generated Autotools files.
- No runtime dependencies beyond libc and sockets.
- Accepts the `aarch64-unknown-linux-ohos` triple via a small config.sub patch.
- Uses umask 022 for configure temp dirs on HMDFS.
- Upstream ships no automated test suite; verification is done by
  installed-package consumers exercising packet init/validate/options,
  destination helpers, and error strings.

## Dependencies

None.

## References

- https://github.com/hhromic/libe131
- https://github.com/hhromic/libe131/releases/tag/v1.4.0
