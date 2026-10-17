# canlock 3.3.1 HarmonyOS adaptation notes

- Official source: `libcanlock-3.3.1.tar.bz2` from the upstream project website.
- Build system: Autotools with Clang; both armv8 and x86_64 HarmonyOS PC targets are accepted. Local verification completed Linux Conan builds plus shared and static OHOS x86_64 Conan cross-builds whose full consumer suites ran on an OpenHarmony 6.0 PC virtual machine. The first native aarch64 OHOS worker run exposed the old `config.guess` limitation documented below.
- Runtime dependencies: none.
- Build dependencies: `bison/3.8.2` and `flex/2.6.4`, both verified as published in the `ohpcd` Conan remote.
- Enabled functionality: core RFC 8315 library, version 2 compatibility API, header-parser library, three command-line tools, and pkg-config metadata.
- Relocatability fix: the header-parser library resolves `canlock-mhp` and `canlock-hfp` through the Conan run environment instead of embedding the build machine's absolute package prefix.
- Cross-build fix: both bundled `config.sub` files accept the `linux-ohos` target triplet emitted by the Conan OHOS profile.
- Native-build fix: both bundled `config.guess` files map HarmonyOS `uname` results to canonical `linux-ohos` triplets. This covers the aarch64 CI worker as well as x86_64 HarmonyOS PC.
- HMDFS fix: both generated `configure` scripts create their `config.status` work directories with umask 022 instead of 077, preventing `subs1.awk: Permission denied` on the native worker's shared build filesystem.
- Consumer run environment: the recipe explicitly prepends the package `bin` directory to `PATH`, including for static consumers whose parser API launches the helper executables.
- Build layout: the recipe builds in the exported source tree because upstream's recursive Automake rules assume generated headers and documentation templates share that tree.
- Shared build testing: upstream test executables link the build-tree static archives directly, so the recipe builds both forms for `make check` and removes static archives from the final shared package.
- Upstream inventory: 18 Automake tests. The declared upstream result is 14 PASS, 2 SKIP, and 2 XFAIL.
- Consumer coverage: fixed SHA-256 vectors, valid and invalid verification, installed hp parser execution, all three CLI version paths, and an OHOS-only SHA-512/secret-clearing test. Both shared and static OHOS consumers were executed on the target VM.

Verification covered Linux shared/static Conan builds, OHOS x86_64 shared/static
cross-builds, and execution of both consumer tests and all three CLI tools on an
OpenHarmony 6.0 PC virtual machine.
