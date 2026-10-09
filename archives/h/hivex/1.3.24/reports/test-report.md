# hivex 1.3.24 verification report

## Environment

- OpenHarmony/HarmonyOS PC aarch64 real device
- Clang 15.0.4 (`ci/conan/profiles/ohos-aarch64`, os=OHOS 6.0 / armv8)
- Conan 2.29.1

## Verification

- `conan-verify hivex 1.3.24`: exit 0 — G0/G1/G2/G3/G4 PASS
- `CI_PACKAGES="archives/h/hivex/1.3.24" zsh ci/conan/build_and_test.sh`: exit 0
- L0: passed
- L1 (test_package): passed
- L2: skipped by the script's platform smoke-test rule (library-only package, no `bin/`)
- L4: skipped — the package contains only `libhivex.a`, which is not an ELF image
- L5: skipped — same reason, no ELF baseline to compare

## Layer 1 — upstream suite (`make check`)

`build()` ends with `autotools.make(target="check")`. `lib/Makefile.am`
registers exactly one C test:

```
check_PROGRAMS = test-just-header
TESTS = test-just-header
```

`lib/test-just-header.c` `hivex_open()`s the bundled `images/minimal` registry
image and fails if the handle is NULL.

- Test cases: 1
- Passed: 1
- Failed: 0
- Skipped: 0

## Layer 2 — test_package (consumer, end to end)

`test_package/test_hivex.c` drives the installed library the way a real consumer
does, in two phases, and is run both through `ctest` and directly:

1. **producer** — reopens the `minimal.b64` fixture (base64 text, decoded to a real hive image at runtime) with `HIVEX_OPEN_WRITE`, grows
   `root/Software/OHOSVendor/hivex`, writes five value types (`REG_SZ`,
   `REG_DWORD`, `REG_QWORD`, `REG_MULTI_SZ`, `REG_BINARY`) via
   `hivex_node_set_value`, then `hivex_commit()`s the result to a new hive;
2. **consumer** — reopens the committed hive read-only, resolves keys and values
   *by name*, reads every value back through the typed accessors, checks the
   structure (child/value counts, parent links, full recursive tree walk) and
   the error paths (unknown key/value, non-existent file).

- Test cases: 1 binary / 37 assertions
- Passed: 37
- Failed: 0
- Skipped: 0

## Result

The recipe was verified on an OpenHarmony aarch64 device and is eligible for
published status.
