# cb0r 1.0.0 HarmonyOS adaptation notes

## Scope

- Package path: `archives/c/cb0r/1.0.0`
- Branch: `feat/cb0r-1.0.0`
- Issue: 待补

## W0 dependency check

cb0r is a single-file C library with zero external dependencies. No Conan dependency packages need to be pre-published.

## Source and build-system analysis

- Source URL: `https://codeload.github.com/quartzjer/cb0r/tar.gz/42d5bfd4a7555298776d023f3033a8a7a8857eec`
- SHA256: `985c7dace12434054da546780b07b74fc97b70a468a720b8318e39e4ee235e5e`
- Commit: `42d5bfd4a7555298776d023f3033a8a7a8857eec` (2024-11-18)
- Upstream repo: https://github.com/quartzjer/cb0r
- License: UNLICENSE (public domain)
- Build system: bare Makefile with hardcoded `gcc -std=gnu99 -Wall`. No configure/CMake/Meson.
- Upstream files:
  - `src/cb0r.c` (11.9 KB) — full CBOR decoder/encoder implementation
  - `src/cb0r.h` (2.9 KB) — public API header
  - `test/test.c` + `test/unit_test.h` — unit tests
  - `bin/cb0r.c` — CLI tool (not packaged; users who need it can build from source)
  - `samples/cases.cbor` — CBOR test vectors

### Packaging strategy

- Compile `src/cb0r.c` directly with the Conan-provided C compiler (bypassing the upstream Makefile).
- Produce `libcb0r.a` (static library) and install `cb0r.h` into `include/`.
- The CLI tool `bin/cb0r.c` is not installed; it is a debugging/sample tool, not a library deliverable.

## API surface

The library exposes 7 functions via `cb0r.h`:

| Function | Purpose |
|----------|---------|
| `cb0r()` | Core parse: walk raw CBOR bytes, optionally skip items, fill result struct |
| `cb0r_read()` | Safer wrapper: parse a complete CBOR item from a buffer |
| `cb0r_get()` | Index into an array/map by position |
| `cb0r_find()` | Look up a key in a CBOR map |
| `cb0r_write()` | Write a CBOR header for a given type + value |
| `cb0r_value()` | Return pointer to item's content bytes |
| `cb0r_vlen()` | Return content byte length |

## Tests

### Upstream tests (compiled in `build()`)

The recipe compiles `test/test.c` against `src/cb0r.c` and runs it during `build()`. The test covers:

- Unsigned integers (1-byte through 8-byte)
- Negative integers
- Byte strings
- UTF-8 strings
- Arrays (empty, flat, nested)
- Maps
- Sequential item parsing and skip
- `cb0r_read` wrapper

### test_package consumer test

The `test_package/test.c` exercises:

1. Parse unsigned int 1 → `CB0R_INT`, value 1
2. Parse unsigned int 256 → `CB0R_INT`, value 256
3. Parse negative int -1 → `CB0R_NEG`
4. Parse byte string "hello" → `CB0R_BYTE`, length 5
5. Parse UTF-8 string "a" → `CB0R_UTF8`, length 1
6. Parse empty array → `CB0R_ARRAY`, count 0
7. Parse array [1, 2] → `CB0R_ARRAY`, count 2
8. Parse map {"a": 0} → `CB0R_MAP`, count 2
9. `cb0r_read` on unsigned 24
10. `cb0r_get` index 1 of [1, 2, 3]
11. `cb0r_write` round-trip for value 42
12. `cb0r_find` key 1 in {1: 2, "a": 3}

Total assertions: 38

## No patches needed

cb0r uses standard C99 with no platform-specific code. The GCC pragma warnings in `cb0r.c` are benign with clang (ignored or silently accepted). No patches were required for OHOS compatibility.

## Next device or shadow CI command

Run only this package when a device/shadow CI slot is available:

```sh
CI_PACKAGES="archives/c/cb0r/1.0.0" zsh ci/conan/build_and_test.sh
```

Shadow CI runner form:

```sh
/path/to/run-ohos-shadow-ci.sh archives/c/cb0r/1.0.0
```

## HarmonyOS real-device shadow CI verification

Run date: 2026-08-21

Commit: `81c8557479` (`fix(cb0r): 从 compiler_executables dict 取 ar，避免非法 conf 键`)

Command (on-device, via `run-ohos-shadow-ci-local.sh`):

```sh
sh "$HOME/validation/run-ohos-shadow-ci-local.sh" archives/c/cb0r/1.0.0
```

RUN_DIR:

```text
/storage/Users/currentUser/ohpc-ci-shadow/runs/81c855747917-20260821T082051Z-55869
```

Result:

- Build Summary: `Total: 1`, `Success: 1`, `Failed: 0` (100%).
- L0: pass — L0j version collision ok (first publish), L0k library package (no commands.json), L0m directory structure valid.
- L1: pass — `test_package` executed, printed `test cb0r 1.0.0: PASS`; L1e negative test confirmed the consumer test genuinely depends on cb0r.
- L2: skip — library package, no `bin/` directory.
- L4: pass — no patches applied.
- L5: pass — `lib/` has content (`libcb0r.a`).
- Package contents: `include/cb0r.h`, `lib/libcb0r.a`, `licenses/UNLICENSE`.

Note: upstream `test/test.c` compiled and ran successfully inside `build()` (visible as the `cb0r_test` step before packaging).

