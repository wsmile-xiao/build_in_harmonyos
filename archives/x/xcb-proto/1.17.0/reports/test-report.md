# xcb-proto 1.17.0 test report

## Environment

- Target: HarmonyOS PC, HongMeng Kernel 1.12.0, aarch64.
- Conan profile: `os=OHOS`, `os.version=6.0`, `arch=armv8`, Release.
- Python: 3.12.9.
- Conan: 2.29.1.
- Source: official X.Org `xcb-proto-1.17.0.tar.xz`.
- Source SHA256: `2c1bacd2110f4799f74de6ebb714b94cf6f80fb112316b1219480fd22562148c`.

## Test counts

| Scope | Classification | Count | Result |
|---|---:|---:|---:|
| Upstream `check-local` schema suite | Other | 1 | 1 PASS |
| Distinct installed protocol generator inputs | Unit/component | 32 | 32 PASS |
| Distinct public `xcbgen` API fixtures | Unit/component | 22 | 22 PASS |
| Installed metadata and discovery | Integration | 1 | 1 PASS |
| Adapted workflows | Total | 55 | 55 PASS |

The upstream suite ran `xmllint` once over all 32 unique XML inputs and printed
that every document validates against `xcb.xsd`. It is one upstream test entry,
not 32 additional adapted cases.

Each adapted protocol case is a separate process with a different XML input
and performs generator registration plus recursive type resolution. Each API
case is also a separate process and uses a fixture for a different public
semantic branch. The metadata process is a separate installed-consumer flow.
There are 55 explicit top-level pass/fail checks. No assertion splitting,
shared/static repetition, repeated input, or fabricated platform case is
included.

Following the existing E239 pattern, the Conan scheduler catches only
command-level `ConanException` failures for these independent processes,
preserves each case label and original error,
continues through all 55 entries, and raises one aggregate failure at the end.
A regression harness injected two separated command failures and confirmed
that the final metadata workflow still ran and both diagnostics survived;
an injected non-Conan exception retained fail-fast behavior and its traceback.
This scheduler regression is evidence for completeness, not another software
test case.

## Command

```bash
CONAN_HOME=<fresh-home> conan create archives/x/xcb-proto/1.17.0 \
  -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build='*'
```

The command returned 0. Its package summary was:

```text
upstream schema check validated 32 protocol XML files
package(): Packaged 32 '.xml' files
package(): Packaged 1 '.xsd' file: xcb.xsd
package(): Packaged 7 '.py' files
package(): Packaged 1 '.pc' file: xcb-proto.pc
validated 32 independent protocol generator workflows
validated 22 independent xcbgen API workflows
validated 1 installed-package metadata workflow
```

Raw log: 242 lines, SHA256
`4673326dbdf61031dc61364457f1d261eb232e0d1eaae193977fbe51fc594448`.
