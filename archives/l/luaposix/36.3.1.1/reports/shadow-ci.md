# Shadow CI report

## Attempt 1: version collision

- Date: 2026-08-13
- Commit: `266394b9bce2fa44b4616676472daabdf2b29b1d`
- Requested package: `archives/l/luaposix/36.3.1`
- Archive SHA-256: `7ea3c80f7f25bd69a31da0300a73bd6711e74ef5cccad816b25d21987627b13e`
- Preflight: pass
- Setup: pass
- Conan: 2.29.1
- Target: OHOS/aarch64, Clang 15
- Discovered packages: 1
- Build result: stopped at L0j before `conan create`
- Gate: `L0_RESULT=fail: gate failed: version_not_incremented`

Run root:

```text
/storage/Users/currentUser/ohpc-ci-shadow/runs/266394b9bce2-20260813T034843Z-run-1931
```

The OHPCD remote already contains `luaposix/36.3.1` recipe revision
`38ed11f234935205f489d427c8102449`, built for Lua 5.5. The registry does not
allow a different recipe under that version. Per the L0j/R37 guidance, the Lua
5.4 adaptation moves to `luaposix/36.3.1.1`; the remote has no such version.

## Attempt 2: build interpreter missing

- Commit: `ad7ea5d00aacb5772a304a2dddda6524cfe9a8b2`
- Archive SHA-256: `53eecf0d370aa1f9b0f9348fd8886643436c6bfface3056059680ce6a4901c5a`
- Preflight and setup: pass
- L0: pass
- L1: fail before compilation
- L2/L4/L5: not run
- Failure: build-context `lua/5.4.8` has no `bin/lua`

Run root:

```text
/storage/Users/currentUser/ohpc-ci-shadow/runs/ad7ea5d00aac-20260813T041956Z-run-19833
```

The downloaded Lua 5.4 package contains headers and `lib/liblua.a`, but no
interpreter. The device also has no system Lua. The corrected recipe uses
published `lua/5.5.0` only as the interpreter for the ABI-independent `luke`
build script; host compilation continues to use `lua/5.4.8`.

## Attempt 3

- Commit: `031a6ea038c1878e8688cd1ece77dc9542a1fb0e`
- Archive SHA-256: `2ce67de225971a7ed6928feed0681d86df784fe7bf608e163ec3b70ea51303ce`
- Status: pass
- L0: pass
- L1: pass, `test_package` executed
- L2: skip, no `bin/` directory
- L4: pass, patches clean
- L5: pass, `lib/` has content
- Package contents: 28 `.so` files and 9 `.lua` files
- Test: all five Lua 5.4 assertions passed, including `posix.signal`

Run root:

```text
/storage/Users/currentUser/ohpc-ci-shadow/runs/031a6ea038c1-20260813T043915Z-run-30865
```

## Attempt 4: review fix

- Commit: `522e0660105a0b8595b0e311c222295d4a0add0f`
- Status: pass
- L0: pass
- L1: pass, all six `test_package` assertions executed
- L2: skip, no `bin/` directory
- L4: pass, patches clean
- L5: pass, `lib/` has content
- Package summary: 1/1 successful, 100%

Run root:

```text
/storage/Users/currentUser/ohpc-ci-shadow/runs/522e066010-20260813T093420Z-run-47294
```

This run verifies the review fix that passes explicit upstream metadata to
`luke`. A separate device-side upstream subset then passed 12/12 expectations
from two unmodified `specl` files. See `review-fix.md` for exact coverage and
the formal CI infrastructure incident.
