# reop 2.1.1 on HarmonyOS PC

## Source and dependency

- Upstream release tarball: `https://pkg.freebsd.org/ports-distfiles/reop-2.1.1.tgz`, SHA-256 `fa8ae058c51efec5bde39fab15b4275e6394d9ab1dd2190ffdba3cf9983fdcac`.
- C source, GNUmakefile; the track labels it C++ but the entire program is C.
- `libsodium/1.0.22` recipe was downloaded from `ohpcd` with `conan download --only-recipe`; its static binary was built locally from that published recipe.
- Target: OpenHarmony 6.1.0.115, aarch64, Clang 15, Conan 2.29.1. The local Conan profile requires `-s os.version=6.0` because its settings schema has 5.0 and 6.0 but no 6.1.

## Native build and fixes

The unmodified source fails under Clang 15 with missing `b64_ntop`/`b64_pton` declarations, two old-style function definitions, and a `sizeof` warning treated as an error. `0001-clang-c99-compatibility.patch` fixes these without changing the cryptographic algorithm. It also puts `-lsodium` after the object files so static linking works.

The recipe downloads and verifies the tarball, applies the patch, then invokes `make -f GNUmakefile -j1` with Conan's libsodium include and library paths. It runs upstream `tests/test.sh` in the build tree. `package()` installs `reop`, its man page, and the upstream ISC notice extracted from `reop.c`.

## Verification

On the HarmonyOS PC, `conan create . -s os.version=6.0 -r=ohpcd --build=missing` compiled with the upstream `-Wall -Werror` flags; `tests/test.sh` returned `All passed.`. The Conan `test_package` used the packaged executable to generate a keypair, sign and verify a message, encrypt and decrypt it, and compare the restored bytes. All passed.

Upstream `tests/test.sh` is one script containing key generation, text and binary encryption round trips, signature verification, and negative signature verification. It writes to its own build-tree test directory; the consumer test uses a fresh dedicated directory on every run.
---

**编译结束**: 2026-10-03 13:55
**最终状态**: built（本机验证通过，等待 CI 上传）
