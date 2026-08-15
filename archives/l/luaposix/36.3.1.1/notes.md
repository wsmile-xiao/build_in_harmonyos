# luaposix 36.3.1.1 adaptation notes

## Scope

Issue #2117 adds a Lua 5.4 ABI package for upstream luaposix 36.3. The existing
`luaposix/36.3` and `luaposix/36.3.1` recipes are published Lua 5.5 contracts
and remain unchanged. The first shadow CI run proved that `36.3.1` had already
been published with a different recipe revision. Following the repository's
R37 collision guidance, this Lua 5.4 compatibility fix therefore uses
`36.3.1.1`.

This package unblocks the Lua 5.4 dependency graph used by `acf-openssh/0.11.2`.
The acf-openssh recipe is not included in this branch.

## Local prerequisite validation

- W0: the official OHPCD remote contains the `lua/5.4.8` recipe and matching
  OHOS/armv8 binary; an install with `--build=never` succeeds.
- The official v36.3 source URL and SHA-256 were downloaded and rechecked.
- The recipe, YAML metadata, patch, shell syntax, and OHOS Conan graph pass
  local static checks.
- A local Windows `conan create` is intentionally not attempted: the recipe
  produces POSIX C modules and requires an OHOS/Linux build host.
- The 26 upstream `specl` files are inventoried but excluded from this package
  smoke test because their seven extra test-only Lua dependencies are not
  published for OHOS and must not be bundled into this dependency recipe.
  A true-device harness nevertheless launched all 26 files individually. The
  16-file OHOS-runnable subset then passed 1147/1147 expectations; the other
  10 files and their platform-specific failure classes are recorded in
  `reports/review-fix.md`.

## Shadow CI validation

Commit `522e0660105a0b8595b0e311c222295d4a0add0f` passed the targeted
OHOS/aarch64 shadow run. L0, L1, L4, and L5 passed; L2 skipped because the
package has no `bin/` directory. The build produced 28 C modules and 9 Lua
files. The test package created a Lua 5.4 state from `liblua.a`, loaded both
`posix` and `posix.signal`, and verified upstream version `36.3`.

Run root: `/storage/Users/currentUser/ohpc-ci-shadow/runs/522e066010-20260813T093420Z-run-47294`

Reproduction command:

```sh
CI_PACKAGES="archives/l/luaposix/36.3.1.1" zsh ci/conan/build_and_test.sh
```

Equivalent shadow runner command:

```sh
/path/to/run-ohos-shadow-ci.sh archives/l/luaposix/36.3.1.1
```

Direct device fallback, using isolated Conan state and the project OHOS
profiles:

```sh
cd archives/l/luaposix/36.3.1.1
export TMPDIR="$RUN_DIR/tmp"
mkdir -p "$TMPDIR"
conan create . --user=ohpcd --channel=stable \
  -pr:h="$CONAN_HOME/profiles/ohos" \
  -pr:b="$CONAN_HOME/profiles/ohos" --build=missing
```

Expected evidence: one discovered package, L0/L1/L5 pass, L2 library skip,
and all six `test_package` assertions pass with Lua 5.4.
