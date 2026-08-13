# E216 - Makefile-only C libraries need direct Conan build and linker runtime env on OHOS runners

## Error Signature

This pattern was observed while adapting `lua/5.1` for HarmonyOS PC:

- `/system/bin/sh: make: inaccessible or not found`
- `cmake: inaccessible or not found`
- `Error loading shared library libxml2.so.16`
- `Error relocating .../ohos/native/llvm/bin/lld: xmlFreeDoc: symbol not found`

## Trigger Conditions

- The upstream project is a small C library with a hand-written Makefile.
- The Conan PR runner does not expose usable `make` or `cmake` to recipe/test_package subprocesses.
- The OHOS SDK compiler invokes `lld`, but the SDK `ohos/native/llvm/lib` directory is not in `LD_LIBRARY_PATH`.
- Downstream packages need the C API and static library more than packaged CLI tools.

## Root Cause

There are two independent runner constraints that can stack together:

1. The normal upstream build entry (`make`, or CMake in `test_package`) is unavailable in the non-interactive Conan runner.
2. The SDK linker executable depends on libxml2 runtime symbols from the SDK LLVM library directory. Some workers do not preload that directory into `LD_LIBRARY_PATH`.

For `lua/5.1`, the package could compile object files but failed when linking the build-tree `lua` executable because `lld` could not load libxml2 symbols.

## Recommended Approach

Mirror the upstream Makefile source list inside the Conan recipe and build directly:

1. Read the upstream Makefile and list core/library/tool sources explicitly in the recipe.
2. Compile with the profile compiler from `tools.build:compiler_executables`.
3. Archive the static library with `llvm-ar` and `llvm-ranlib`.
4. Around every clang link command, create a Conan `Environment`, prepend the discovered OHOS SDK `ohos/native/llvm/lib` directory to `LD_LIBRARY_PATH`, and apply it with `env.vars(self).apply()`.
5. Run the upstream smoke test from the build tree before packaging.
6. In `test_package`, avoid CMake if the runner does not provide it; compile the consumer test directly with clang using dependency `cpp_info` include/lib/system library data.

## Packaging Boundary

If downstream consumers only need the library, package the dependency surface instead of forcing CLI tools into `bin`:

- install headers, static library, man pages, and license;
- keep `cpp_info.bindirs = []`;
- let generic PR CI skip L2 CLI smoke because no `bin/` directory is packaged;
- still build the upstream executable in `build()` if needed to run upstream smoke tests.

This avoids treating upstream CLI option differences, such as Lua 5.1 not supporting `--version`/`--help`, as package failures for a library dependency.

## Validation

For `lua/5.1`, the fixed PR build passed after adding the linker environment:

```text
PR #4635 build #22585 PASS
```

The recipe also keeps a consumer test that verifies `luaL_newstate`, `luaL_openlibs`, `luaL_loadstring`/`lua_pcall`, `_VERSION`, `package`, and `require`.

## Related Entries

- E011: manual Makefile/manual source-list style fallback.
- E132: OHOS SDK `lld` requires SDK LLVM lib path for libxml2 runtime symbols.
