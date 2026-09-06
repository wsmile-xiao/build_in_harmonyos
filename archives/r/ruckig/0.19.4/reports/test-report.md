# Test report

## Current status

| Environment | Build | Upstream tests | Consumer tests |
|---|---:|---:|---:|
| Windows x86_64, cloud client ON | pass | 21/21 | not packaged in this mode |
| Windows x86_64, cloud client OFF | pass | 21/21 | 18/18 |
| HarmonyOS PC, aarch64 | pass | 21/21 | 18/18 |

## Upstream inventory

| Type | Discovered | Executed | Passed | Failed | Skipped |
|---|---:|---:|---:|---:|---:|
| Doctest unit/property cases | 15 | 15 | 15 | 0 | 0 |
| Local integration examples | 6 | 6 | 6 | 0 | 0 |
| Other | 0 | 0 | 0 | 0 | 0 |
| Total | 21 | 21 | 21 | 0 | 0 |

Each host cloud configuration also ran 5,000,000 randomized trajectories and
reported 26,250,183/26,250,183 passing dynamic assertions. HarmonyOS ran the
same workload with 26,250,188/26,250,188 passing dynamic assertions. CTest
independently reported its single registered harness as 1/1 passed.

## Consumer test inventory

The single portable C++ entry contains four functional cases and 18 assertions:

1. Valid input acceptance and offline calculation.
2. Start, midpoint, and terminal trajectory sampling.
3. Online update completion and terminal-state accuracy.
4. Invalid negative jerk limit rejection.

The normal test is executed by Conan. A separate negative control passes
`--self-test-failure` and must return 1, proving failure propagation without
counting an intentional failure as a package test. The same binary and
`run_test.sh` are the HarmonyOS device entry, so device and Conan conclusions
share test logic and assertions.

Native `conan create` completed with exit 0 and built the shared package before
running the consumer test. On HarmonyOS, `conan-verify` and W3 local CI passed;
the copied minimal package passed 18/18 and the negative control returned 1. The
repository `ohc-run.py conan-verify` wrapper reached G0/G1 but its Windows host
run stopped before Conan with `[WinError 2]` because its command construction is
POSIX-specific. The subsequent HarmonyOS wrapper execution passed and is the
target-platform result.

## Evidence

Raw host and HarmonyOS logs are retained outside the PR under
`output/ruckig-0.19.4/`. The authoritative W3 log SHA256 is
`8db7bfff14c07982dc036e3d581cc684a162b6a5428fe10ab989894db67957d2`.
