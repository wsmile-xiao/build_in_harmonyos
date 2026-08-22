# Test report: aicommit2 2.8.0

Date: 2026-08-21

## Source identity

The npm registry metadata for `aicommit2@2.8.0` identifies upstream git commit:

```text
57ee029ecc9e22b4373b8a4dc6cff96caa043dda
```

The complete source and test tree for that commit was retrieved into an
isolated temporary directory. All 153 retrieved files were verified against
the official GitHub tree blob SHA-1 values before dependency installation.
The npm release used by the Conan recipe remains independently pinned by
SHA256 `a5d30aedbebe8ae9017f1ef86bfdb5d3e2cc20ef3a5a999a14e88450ba28a96c`.

## Official upstream suite

Environment:

```text
Windows 11
Node.js 24.19.0
pnpm 11.16.0
```

Commands:

```text
pnpm install --frozen-lockfile --ignore-scripts --registry=https://registry.npmjs.org
pnpm build
pnpm test
```

The official command was run twice with the same result:

```text
registered: 380
passed:     377
failed:     3
pass rate:  377/380 (99.21%)
```

The three failures are reproducible Windows platform differences:

1. `aicommit2 > config > set config file`: upstream expects LF-only output,
   while the Windows INI writer emits CRLF.
2. `aicommit2 > config > get config file`: the same LF/CRLF exact-string
   difference.
3. `aicommit2 > CLI > rewrite command > Accepts --dry-run with valid repo`:
   assertions complete, then `fs-fixture` cleanup receives Windows `EBUSY`
   while removing the temporary repository.

Provider-backed suites are skipped by the upstream runner when their
credentials are absent. The upstream runner also skips TTY-specific cases on
Windows. These exclusions are not reported as passes. The raw pass rate above
uses the 380 tests actually registered by the official runner.

## Release and package checks

The official npm release smoke command passed all four assertions:

```text
sh run_smoke_tests.sh <source-dir>
4/4 passed (100%)
```

The Conan consumer test exercised the package-owned launcher and passed all
five assertions:

```text
sh test_package/test.sh <aicommit2-path>
5/5 passed (100%)
```

These checks cover the reported version, command registration, help output,
and `config --help`. The HarmonyOS package-specific total is therefore:

```text
9/9 passed (100%)
```

## Conclusion

The full official upstream suite has been executed and its raw pass rate is
reported without converting platform failures or upstream exclusions into
passes. Package-specific deterministic functionality is 9/9 on HarmonyOS, and
the separate Shadow CI report records the successful Conan validation.
