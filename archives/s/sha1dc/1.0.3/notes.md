# sha1dc 1.0.3 HarmonyOS adaptation notes

## Scope

- Worktree: `D:\harmonyos\worktrees\sha1dc`
- Branch: `feat/sha1dc-1.0.3`
- Archive path: `archives/s/sha1dc/1.0.3`
- Issue: #1556

## W0 dependency check

sha1dc 1.0.3 has no required third-party build dependencies. The recipe does not declare Conan requirements.

Remote checks from this Windows host:

```text
conan download "sha1dc/1.0.3" -r=ohpcd --only-recipe
=> ERROR: error:system acceleration policy not enabled. [Remote: ohpcd]
```

Because the remote query is blocked by local network/acceleration policy, final PR verification should re-run the single-package CI command in the normal OHOS/shadow CI environment.

## Source and build system analysis

- Upstream: `https://github.com/cr-marcstevens/sha1collisiondetection`
- Version tag tarball: `https://codeload.github.com/cr-marcstevens/sha1collisiondetection/tar.gz/refs/tags/stable-v1.0.3`
- sha256: `77a1c2b2a4fbe4f78de288fa4831ca63938c3cb84a73a92c79f436238bd9ac07`
- Build system: plain POSIX Makefile.
- Public header: `lib/sha1.h`.
- Library output: `bin/libsha1detectcoll.a` when libtool is not used.
- CLI outputs: `bin/sha1dcsum`, `bin/sha1dcsum_partialcoll`.

The upstream Makefile detects `libtool` and otherwise builds a static `.a`. This recipe forces `LIBTOOL=__conan_no_libtool__` to keep the package static-only and avoid shared-library/signing/RPATH issues in first OHOS validation.

On OHOS the clang wrapper injects `-Wl,--code-sign` even for compile-only dependency generation. Upstream uses `-Werror`, so the recipe adds `-Wno-error=unused-command-line-argument` to keep that wrapper warning from aborting the build.

The OHOS filesystem can leave freshly linked `test_package` binaries without execute bits, so the test recipe signs the binary when tools are available and always applies `chmod 755` before executing it.

The CLI smoke test invokes `sha1dcsum` from the dependency bindir instead of relying on `PATH`, because this CI environment did not expose package `bin/` through `VirtualRunEnv` for this library package.

Packaged CLI binaries are chmodded after signing because `binary-sign-tool` can create replacement files without execute bits.

## Upstream tests

Upstream provides a `check` target:

```text
make check
```

It builds the command-line tools and verifies hashes for bundled collision fixtures:

- `test/sha1_reducedsha_coll.bin`
- `test/shattered-1.pdf`
- `test/shattered-2.pdf`

The Conan recipe runs this target during `build()`.

## Consumer test

`test_package` performs two checks:

- Compiles and runs a C program that includes `<sha1dc/sha1.h>`, calls `SHA1DCInit`, `SHA1DCUpdate`, `SHA1DCFinal`, and verifies SHA-1(`abc`) equals `a9993e364706816aba3e25717850c26c9cd0d89d`.
- Executes packaged `sha1dcsum` on `sample.txt` through `VirtualRunEnv`.

## Local verification

Completed:

- Created isolated worktree and branch.
- Downloaded codeload tarball locally and verified sha256.
- `conan source` passed when the recipe was copied to `D:\harmonyos\tmp\sha1dc-source-check`.
- `conan export archives/s/sha1dc/1.0.3 --user=ohpcd --channel=stable` passed.
- `conan inspect archives/s/sha1dc/1.0.3` passed.
- `python -B -m py_compile` passed for both recipe files.
- `git diff --check -- archives/s/sha1dc/1.0.3` passed.
- Confirmed no existing `archives/s/sha1dc/1.0.3` archive or `sha1dc` branch.
- Confirmed no dependency libraries to split out.

## OHOS single-package CI

Runner:

```text
/storage/Users/currentUser/ohos-test-runs/codex-1.0.3-sha1dc-1.0.3-conan-20260727-231514-12505
```

Result:

```text
exit-code.txt: 0
L0_RESULT=pass: all checks passed
L1_RESULT=pass: upstream tests + test_package executed
L2_RESULT=skip: sha1dcsum version/help failed, sha1dcsum_partialcoll failed
L4_RESULT=pass: no patches
L5_RESULT=pass: bin/ has content
Build Summary: Total 1, Success 1, Failed 0
```

Notes:

- Upstream `make check` passed on bundled reduced-round/shattered fixtures.
- `test_package` API test produced SHA-1(`abc`) = `a9993e364706816aba3e25717850c26c9cd0d89d`.
- Packaged `sha1dcsum` ran successfully against `sample.txt`.
- L2 skip is non-blocking because upstream CLI tools do not provide standard `--help`/`--version` behavior.
- L0k commands metadata warning resolved by adding software-level `archives/s/sha1dc/commands.json`.

Blocked locally:

- `ohpcd` remote query returns `system acceleration policy not enabled`.
- Windows host has no `make` or `clang`, so compile verification was performed on the supplied OHOS machine instead.

## Next verification commands

Single package CI:

```sh
CI_PACKAGES="archives/s/sha1dc/1.0.3" zsh ci/conan/build_and_test.sh
```

Shadow CI:

```sh
/path/to/run-ohos-shadow-ci.sh archives/s/sha1dc/1.0.3
```

Manual Conan smoke on OHOS worker:

```sh
cd archives/s/sha1dc/1.0.3
conan create . --user=ohpcd --channel=stable \
  -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing
```
