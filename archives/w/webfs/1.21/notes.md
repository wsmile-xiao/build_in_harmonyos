# webfs 1.21 — HarmonyOS PC adaptation notes

- Package: `webfs/1.21`, branch `feat/webfs-1.21`.
- Upstream homepage: https://linux.bytesex.org/misc/webfs.html
- Source archive: https://www.kraxel.org/releases/webfs/webfs-1.21.tar.gz
- SHA-256: `98c1cb93473df08e166e848e549f86402e94a2f727366925b1c54ab31064a62a`.
- License: GPL-2.0-only; package type: command-line application.

## Build decisions

- TLS is enabled through the declared `openssl/4.0.1` Conan dependency.
- The project is a plain GNU make build; the recipe explicitly runs make with Conan's generated `conanbuild` environment so the OpenSSL include/link paths and OHOS compatibility define are present during compilation.
- `USE_SENDFILE=no` is explicit because HarmonyOS also defines `__linux__`; this selects upstream's portable buffered transfer implementation rather than the Linux syscall path.
- `WEBFS_MISSING_PASSWD_DB` is a build capability enabled only for `os=OHOS`. The small upstream patch synthesizes passwd/group names only for a non-root process when numeric lookups are absent; it preserves the device's real UID/GID and leaves root lookup failures unchanged. This was required because the HarmonyOS 6.0 test device has no matching passwd/group entries, and unpatched webfsd exits before listening.
- No `/etc/mime.types` is present on the device. Upstream treats this as nonfatal; the HTTP integration test validates status/body independently of MIME database presence.

## Upstream tests

Source inspection of `GNUmakefile`, `mk/Autoconf.mk`, `mk/Compile.mk`, `mk/Maintainer.mk`, and the source tree found no upstream test files or `check`/`test` target. `test_package/MANIFEST.yml` records zero upstream tests and the test package adds ten consumer assertions, including a HarmonyOS-only byte-range test.

## Verification

- `python -m py_compile` passed for the recipe and both test-package Python files; `refresh-patch --auto` generated the combined compatibility patch; the target-side patch dry-run passed.
- `ci/scripts/preflight_check.sh webfs/1.21` passed: `openssl/4.0.1` is published and `webfs/1.21` is not already in the registry.
- `ci/conan/build_and_test.sh`, using `ci/conan/profiles/ohos-aarch64`, passed G0/G0e, L0, knowledge and junk checks, L1, L4, and L5. Conan created the package and ran the test package on HarmonyOS 6.0; A1-A10 passed (10/10). The HarmonyOS-only range assertion returned 206 with the expected `Content-Range` and exact bytes.
- The script reported L2 generic `--version/--help` smoke as skipped: upstream supports `-h`, prints usage, and intentionally exits 1. A1 confirms the expected usage text; this is non-blocking in CI.
- Conan CI exposed two integration details: the OpenSSL CLI is resolved from PATH or HarmonyOS Homebrew, and the plain make invocation must load Conan's `conanbuild` environment. Both are fixed and the final CI rerun passed.
- Non-fatal upstream compiler warnings include pointer-sign conversions and the expected buffered sendfile warning. The build and all functional tests passed.

## Source and patch provenance

- The pinned archive is listed in the webfs release index at https://www.kraxel.org/releases/webfs/; its SHA-256 was verified on the HarmonyOS target. The upstream project page links to dl.bytesex.org, which did not resolve on the target, while the Kraxel release host served the same verified archive.
- The OHOS compatibility patch was generated with python3 scripts/ohc-run.py refresh-patch --auto webfs 1.21 from the verified upstream source and a temporary modified source tree. The manifest records the generated source hashes and patch count.
