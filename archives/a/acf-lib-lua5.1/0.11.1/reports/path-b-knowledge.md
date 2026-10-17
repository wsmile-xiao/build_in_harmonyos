# acf-lib-lua5.1 0.11.1 Path B knowledge evidence

## Claim

This adaptation applies for Path A and is a Path B knowledge-extension
candidate. The Path B contribution is not the reuse of E050, E132, or E216;
it is the new reusable pure Lua module packaging and target-validation pattern
recorded in `knowledge/drafts/E324-draft-ACF51.{kv,md}`.

Final Path B classification remains subject to project review.

## Novelty boundary

| Existing entry | Existing scope | E324 addition |
|---|---|---|
| E050 | Replace HMDFS-incompatible symlinks with copies | Maps the rule to Lua namespace and compatibility imports, then verifies both with target `require` |
| E132 | Add the SDK LLVM library directory while running `lld` | Keeps this link-time prerequisite separate from the pure Lua runtime contract |
| E216 draft | Build the native Lua 5.1 C library and its target runner | Defines how downstream pure Lua source-module packages consume that interpreter |
| E241 | Validate architecture-neutral data/rule packages | Adds interpreter versioning, `LUA_PATH`, executable module loading, and behavior assertions |

## Implementation evidence

| Reusable rule | Evidence in this package |
|---|---|
| Pin and validate source | `conandata.yml`; exact eight-module and non-empty checks in `conanfile.py` |
| Satisfy the target profile without multiplying source artifacts | Full four-setting declaration plus `package_id()` clearing |
| Preserve promised imports without symlinks | Real copies under `share/lua/5.1/acf` and `share/lua/5.1` |
| Export versioned module discovery | Build/run `LUA_PATH` definitions ending in `;;` |
| Use the target interpreter | `test_package/mini_lua.c` links the separate Conan `lua/5.1` package |
| Execute packaged behavior | `test_acf_lib.lua` performs 35 layout, load, success, and error checks |
| Test optional paths without shipping fake dependencies | `upstream_acf_db_test.lua` drives 10 real packaged `acf.db` assertion sites using test-only stubs |

## Reuse decision

Use E324 for pure Lua packages with an interpreter-versioned install root and
runtime imports. Continue using E241 for opaque data/rule sets, E216 for native
Lua runtime builds, E050 for general HMDFS link failures, and E132 for SDK lld
startup failures.

## Verification command

```sh
CI_PACKAGES="archives/a/acf-lib-lua5.1/0.11.1" zsh ci/conan/build_and_test.sh
```

Shadow CI build #24739 passed Conan `test_package`, L0, and L1. The two Lua
scripts are fail-closed on any missing, failed, or skipped check; therefore the
successful test package result proves 45/45 checks executed and passed.
