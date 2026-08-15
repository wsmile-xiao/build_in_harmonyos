# Local validation report

- Date: 2026-08-13
- Issue: #2117
- Package: `luaposix/36.3.1.1`
- Target profile: `OHOS 6.0`, `armv8`, Clang 15, Release
- Result: pass, including targeted native shadow CI

## Passed checks

1. The GitCode issue API returned open P1 issue #2117 for dependency luaposix.
2. The official v36.3 source archive downloaded from GitHub codeload has
   SHA-256 `82cd9a96c41a4a3205c050206f0564ff4456f773a8f9ffc9235ff8f1907ca5e6`.
3. The OHOS `TMPDIR` patch applies to the official source as a zero-context
   unified diff and replaces `os.tmpname` with a `TMPDIR`-aware generator.
4. The upstream rockspec declares `lua >= 5.1, < 5.5`, which includes Lua 5.4.
5. Both recipe Python files pass AST parsing; all three YAML files parse.
6. All package files use LF line endings, UTF-8 without BOM, and pass
   `git diff --check`.
7. The test package has a Lua 5.4 C runner and six Lua assertions.
8. `conan export` succeeds in an isolated Conan 2.29.1 cache; local recipe
   revision before the report-only update was `8f59efa366651e0d9343f4c44154dd50`.
9. `conan graph info` resolves one host `lua/5.4.8` node and one build-context
   `lua/5.5.0` node, with zero invalid nodes.
10. `conan install --requires=lua/5.4.8 --build=never -r=ohpcd` succeeds for
    the OHOS profile. Dependency recipe revision is
    `0780497a27ff34ad52a2d542b7053eec`; package revision is
    `2fccf4fffa570e8bdb01fe8dccacd73c`.
11. The remote already contains a Lua 5.5 `luaposix/36.3.1` recipe revision
    `38ed11f234935205f489d427c8102449`; `luaposix/36.3.1.1` is not published.
12. The first shadow run stopped at L0 because the original version collided
    with the remote recipe. The second passed L0 but found that library-only
    `lua/5.4.8` has no `bin/lua`.
13. The package graph now uses Lua 5.5 only to run the build-context `luke`
    script and preserves Lua 5.4 for all compiled package artifacts.
14. Commit `522e0660105a0b8595b0e311c222295d4a0add0f` passed targeted shadow
    CI. The package contains 28 C modules and 9 Lua files. The Lua 5.4 test
    runner executed all six assertions, loaded `posix.signal`, and verified
    that `posix.version` ends in upstream version `36.3`.

## Shadow gates

- L0: pass
- L1: pass, `test_package` executed
- L2: skip, library package has no `bin/`
- L4: pass, patches clean
- L5: pass, `lib/` has content

The source contains 26 upstream `specl` files. A device-side harness launched
all 26 files individually against the package produced by shadow CI, so one
unsupported facility could not prevent later files from running. Sixteen files
completed successfully and ten exposed platform-specific assumptions or
unsupported facilities. A second run limited to the 16 OHOS-runnable upstream
files exited zero: 16/16 files, 1147/1147 expectations passed, 5 upstream
pending expectations, and zero failures. No upstream YAML expectation or
package artifact was changed. Exact dependencies, failure classes, compatibility
handling, and run roots are recorded in `review-fix.md`.
