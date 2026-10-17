# brag 1.4.3 adaptation notes

## Scope
- Package: `brag/1.4.3`
- Source: `https://sourceforge.net/projects/brag/files/brag/1.4.3/brag%2D1.4.3.tar.gz/download`
- SHA256: `f2c8110c38805c31ad181f4737c26e766dc8ecfa2bce158197b985be892cece6`
- License: `GPL-2.0-or-later`

## Adaptation
- brag 1.4.3 is a pure Tcl script; no target compilation is required.
- Packages the upstream `brag` script, man page, and documentation.
- Rewrites the launcher from `exec tclsh` to `exec tclsh8.6` because the published `tcl/8.6.14` package provides `tclsh8.6`.
- Declares `tcl/8.6.14` as a runtime dependency with `run=True`.
- Declares `uudeview/0.5.20` because brag invokes `uudeview` when decoding downloaded multipart attachments.

## Tests
The release archive does not contain an upstream automated test suite.

The added `test_package` performs deterministic offline smoke tests:
- verifies `brag`, `tclsh8.6`, and `uudeview` are available in the Conan runtime environment;
- verifies Tcl reports version 8.6.14;
- verifies the packaged uudeview executable produces its expected usage output;
- invokes packaged brag with an unsupported `--help` argument and verifies the documented usage path and expected exit code 1.

No NNTP server or network service is required by the smoke tests.

## Local validation
- OHOS armv8 profile: `ci/conan/profiles/ohos-aarch64`
- Conan create: passed.
- Runtime dependency graph contains `tcl/8.6.14` and `uudeview/0.5.20`.
- test_package: all 4 smoke-test groups passed.
---

**编译结束**: 2026-08-12 09:58
**最终状态**: built
