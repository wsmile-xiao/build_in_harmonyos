# waili 19990723 adaptation notes

## Build strategy

- Source: Debian pristine upstream tarball, SHA-256 pinned in `conandata.yml`.
- Build system: the upstream 1999 custom Makefiles, not Autotools/CMake.
- The recipe creates `Rules.config` by running `config/Configure` through an
  available POSIX shell, then builds `lib` and `test` explicitly with `-j1`.
- `CXX`, `AR`, and `RANLIB` come from the Conan profile and build environment;
  the recipe does not use a bare `g++` or shell-expanded `$CXX`.
- `-std=c++17 -stdlib=libc++` is supplied when the profile selects libc++,
  matching the OpenHarmony clang 15 toolchain.
- The package contains `lib/libwaili.a`, all public `include/waili/*.h`
  headers, and all six programs under `bin/`.

## Minimal source patch

`patches/0001-clang-ohos.patch` is the only source patch. It applies the
observed minimal compatibility fixes:

- replace `stream.h` / `iostream.h` with standard headers;
- correct pre-standard array-new syntax and repeated default arguments;
- replace the removed GNU `<?` and `>?` operators;
- repair the malformed `ClearRect` forwarding call; and
- derive `CLK_TCK` through `sysconf(_SC_CLK_TCK)` when it is not a macro.

No algorithm or API behavior is intentionally changed. Rangecheck's obsolete
operators are rewritten so the program builds, but the program keeps its
upstream runtime check that requires `sizeof(PixType) >= 8`.

## Test accounting

Upstream has six demonstration programs and no formal test runner. The
consumer test runs four complete workflows:

- `Example` on a generated PGM;
- `Demo` with the `quit` command;
- `Proof` on a generated PGM; and
- `Test` on a generated PGM, expecting `Maxerr = 0.000000`.

Two limitations are recorded, not counted as passes:

- `Histogram`: the test runs its help path, but the real plotting workflow is
  only run when `gnuplot` is available. Without gnuplot the limitation is
  printed explicitly.
- `Rangecheck`: the packaged program is expected to exit non-zero with
  `PixType must contain 64 bits (now: 16 bits)`. This is an upstream test bug
  because the public `PixType` is `s16`; the test runner asserts that exact
  known failure and labels it as a limitation.

The normal result is therefore **4/4 runnable workflows pass, 1 conditional
workflow skipped without gnuplot, and 1 known upstream failure documented**,
never 6/6.

## Validation status

The recipe and patch should be validated on the OpenHarmony CI worker with:

```sh
CI_PACKAGES=archives/w/waili/19990723 /bin/zsh ci/conan/build_and_test.sh
```

This staging subagent did not submit an OpenDesk job, so `manifest.yaml`
marks the recipe as `pending` rather than claiming an unperformed target run.
