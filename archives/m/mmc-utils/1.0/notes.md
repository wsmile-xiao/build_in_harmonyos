# mmc-utils 1.0 adaptation notes

- Upstream: `https://git.kernel.org/pub/scm/utils/mmc/mmc-utils.git`, tag `v1.0`.
- Source archive SHA256:
  `3be34e30b0830c71d690264ff433c7f8b0613c8ac8eeed71e49f6bcb6bc79772`.
- Source transport uses the official kernel.org cgit snapshot; upstream has no
  GitHub mirror (`linux-mmc/mmc-utils` does not exist, `mhei/mmc-utils` is 404).
- Build system: upstream Makefile (`make -j1`, in-source only).
- Conan dependencies: none (OpenHarmony system C/POSIX interfaces + sysroot
  kernel headers such as `linux/mmc/ioctl.h`).
- Compiler is taken from `tools.build:compiler_executables` (R33) because `${CC}`
  is empty on CI workers.
- `C=0` is passed because the upstream default `C ?= 1` invokes `sparse`, which
  is absent on OHOS and aborts the build with Error 127.
- `GIT_VERSION=1.0` is passed because upstream derives it from `git describe`,
  which yields an empty string when building from a release tarball.
- `package()` copies `mmc` and `mmc.1` directly instead of calling
  `make install`, whose `INSTALL = install` and `mandir = /usr/share/man` do not
  fit OHOS.
- No patches: the tree compiles unmodified, so `patches_applied` is empty.
- The consumer test runs `mmc help` and asserts the usage table plus the `1.0`
  version string. `mmc --version` is not used: unknown commands are rejected
  with exit code 1 upstream, so only `help` prints the version.
- Real-device verification: `conan-verify` passed (G1/G2/G3/G4) and the local CI
  simulation `build_and_test.sh` passed (W3, exit code 0).

---

**编译结束**: 2026-09-26
**最终状态**: built
