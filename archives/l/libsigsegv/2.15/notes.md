# libsigsegv 2.15 · HarmonyOS PC

## Upstream

- Source: https://ftp.gnu.org/gnu/libsigsegv/libsigsegv-2.15.tar.gz
- SHA-256: 036855660225cb3817a190fc00e6764ce7836051bacb48d35e26444b8c1729d9
- Build system: GNU Autotools; no Conan dependencies
- Upstream test list: five unconditional entries in tests/Makefile.am. The Cygwin and EFAULT tests are conditional and are not enabled on HarmonyOS.

## Adaptation

1. config.guess now maps HarmonyOS aarch64, arm, and x86_64 machines to the corresponding linux-ohos triplet.
2. The 2.15 upstream config.sub already accepts aarch64-unknown-linux-ohos.
3. configure uses umask 022 for linux-ohos when creating its temporary directory. This avoids the HMDFS permission failure produced by umask 077 with mktemp.
4. conanfile.py runs the upstream make check suite as part of build().

## Device verification

- conan create exited 0 using the HarmonyOS aarch64 host and build profiles.
- Upstream make check: 5/5 passed: test-catch-segv1, test-catch-segv2, test-segv-dispatcher1, test-catch-stackoverflow1, and test-catch-stackoverflow2.
- Consumer test: 1/1 CTest passed; the direct test binary also reported SIGSEGV capture, stack overflow recovery, and version 2.15.
- The package contains the static library and sigsegv.h.
