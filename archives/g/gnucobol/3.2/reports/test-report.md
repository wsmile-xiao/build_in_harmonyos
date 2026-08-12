# Test Report - GnuCOBOL 3.2

## Build Matrix

| Setting | Value |
|---|---|
| OS | OHOS 6.0 |
| Architecture | armv8 (AArch64) |
| Compiler | clang 15.0.4 |
| Build type | Release |
| Conan package type | shared-library |
| Dependency | gmp/6.3.0, static PIC |

## Clean Build

```bash
conan create archives/g/gnucobol/3.2 \
  -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing
```

Result: PASS, exit code 0. The build downloaded the official GnuCOBOL 3.2 source archive, verified SHA256, applied all five patches, resolved the local verified GMP package, configured, compiled, tested, installed, packaged, and ran test_package.

## Upstream Tests

| Result | Count |
|---|---:|
| Behaved as expected | 1226 |
| Skipped | 56 |
| Unexpected failures | 0 |

The skipped cases require explicitly disabled optional facilities such as indexed database handlers, XML, JSON, or platform-specific functionality. Four initially unexpected tests were diagnosed and fixed:

- Test 8: read-only `/tmp` fallback
- Test 10: `llvm-strip` invalidated HarmonyOS ELF signatures
- Test 667: optimized executable was invalidated by automatic strip
- Test 820: HarmonyOS `fmemopen` was present but nonfunctional

After the platform fixes, all four focused regressions passed and the full clean suite reported `1226 tests behaved as expected`.

## Consumer Tests

| Test | Result |
|---|---|
| Link and run C program using `cob_malloc`/`cob_free` from libcob | PASS |
| Convert a long `cob_field` into an 8-byte guarded buffer without overwriting the sentinel | PASS |
| `cobc --version` reports GnuCOBOL 3.2.0 | PASS |
| `cobcrun --version` reports GnuCOBOL 3.2.0 | PASS |
| Packaged `cobc` compiles `hello.cob` | PASS |
| Generated COBOL executable runs and prints `GnuCOBOL compiler: OK` | PASS |
| Five patches apply cleanly to pristine source | PASS |

## Artifacts

- `bin/cobc`: 1,411,520 bytes
- `bin/cobcrun`: 31,168 bytes
- `bin/cob-config`: 4,369 bytes
- `lib/libcob.so.4.2.0`: 698,816 bytes
- `lib/gnucobol/CBL_OC_DUMP.so`: 31,104 bytes
- libcob headers, compiler configuration, and copybooks included

## W3 Local CI

| Gate | Result | Detail |
|---|---|---|
| L0 | PASS | Recipe, patches, test_package, MANIFEST and R38 checks passed |
| L1 | PASS | Upstream tests and substantive test_package executed |
| L2 | PASS with warning | `cob-config` passed directly; `cobc/cobcrun` require Conan runenv and passed there |
| L4 | WARN, false positive | Scanner matched `gets` inside patch-context word `targets`; no dangerous function added |
| L5 | PASS | `bin/` and package artifacts present |

The W3 pipeline completed with exit code 0 and generated `.ci-result.json` with an integrity hash.

## Known Gate Status

Local compilation and tests pass. Remote publication is blocked by R36 until `gmp/6.3.0` is released to the `ohpcd` Conan remote. The package therefore remains `built`, not `published`.
