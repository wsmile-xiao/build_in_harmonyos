# MGEN

MGEN (Multi-Generator) is the NRL PROTEAN IP network performance test tool.
It generates UDP/TCP traffic from scriptable flows and logs measurements.

This recipe adapts upstream release V5.1.1 (recipe version `5.02.c5.1.1`,
mirroring Debian's `5.02.c+really5.1.1` versioning) to HarmonyOS PC (arm64).

## Binaries

- `mgen` — traffic generator (`mgen help` prints usage)
- `mpmgr` — shared-memory payload manager

## Build

Plain Makefile project (`makefiles/Makefile.linux`); the bundled protolib
submodule is fetched as a second source archive. Zero external dependencies
(optional HAVE_PCAP disabled on OHOS).

## Tests

Upstream ships no automated test suite. `test_package/test_mgen.sh` runs
8 runtime consumer cases against the packaged binaries
(`mgen help` output assertions, mpmgr existence, unknown-command no-hang
probe) without sending any network traffic.

## References

- Upstream: https://github.com/USNavalResearchLaboratory/mgen
- License: NRL permissive notice (see LICENSE in source)
