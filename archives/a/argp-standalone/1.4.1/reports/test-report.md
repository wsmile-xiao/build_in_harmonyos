# argp-standalone 1.4.1 verification report

## Environment

- OpenHarmony/HarmonyOS PC aarch64 real device
- Clang 15.0.4 (aarch64-unknown-linux-ohos, musl)
- Conan 2.29.1 (OHOS adapted)

## Upstream tests (make check)

Executed on the real device after configure + make:

```
srcdir="." ./run-tests  ex1-test permute-test
PASS: ex1
PASS: permute
==================
All 2 tests passed
==================
```

- Test cases: 2 (ex1-test, permute-test)
- Passed: 2
- Failed: 0
- Skipped: 0
- **Pass rate: 100%**

## Conan verification

- `conan-verify argp-standalone 1.4.1`: exit 0
- G0 pre-build risk: PASS
- G1 recipe completeness: PASS
- G2 conan create (clean build): PASS
- G3 system-library isolation (R26): PASS
- G4 artifacts completeness: PASS
- L2/L4/L5: skipped (pure static library, no executable smoke target)
- W3 local CI (`finish` step 5): PASS — `.ci-result.json` exit_code=0,
  integrity_hash=6aad22d78343032b

## test_package (consumer view, R34)

`test_probe` is compiled with clang++ against libargp.a and executed on
the device (`-static-libstdc++`). It drives `argp_parse()` through a real
command-line parse round trip and asserts:

1. `argp_program_version` can be set and read back
2. `--verbose` long option recognized
3. `-o FILE` short option with value
4. `--output=FILE` equals form gets value
5. positional args reach `ARGP_KEY_ARG`
6. multiple positionals each reach the callback
7. unknown option returns non-zero without exiting the process

Result from conan create log:

```
[ok] argp_program_version can be set and read back
[ok] parse --verbose -o out.txt input.bin returns 0
[ok] long option --verbose recognized
[ok] short option -o got value out.txt
[ok] positional arg reaches ARGP_KEY_ARG
[ok] long option equals form --output=eq.txt gets value
[ok] all three positional args reach callback
[ok] unknown option returns non-zero (without exiting process)
argp-standalone 1.4.1: all assertions passed
```

- Test cases: 8 assertions
- Passed: 8
- Failed: 0
- **Pass rate: 100%**

## Result

The recipe was verified on an OpenHarmony aarch64 device and is eligible
for built/published status.
