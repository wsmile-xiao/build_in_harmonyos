# glibmm 2.66.7 test report

## Results

| Suite | Discovered | Executed | Passed | Failed | Excluded |
|---|---:|---:|---:|---:|---:|
| Upstream Meson tests | 34 | 33 | 33 | 0 | 1 |
| Conan consumer assertions | 9 | 9 | 9 | 0 | 0 |

## Commands and interpretation

- The recipe executed `meson test -v -C <build-folder> --timeout-multiplier=16 --no-rebuild --no-suite=failing` on native HarmonyOS PC.
- Meson `intro-tests.json` listed 34 upstream test programs.
- The command genuinely executed 33 programs and reported `Ok: 33`, `Fail: 0`.
- `giomm_tls_client_test` was assigned to the `failing` suite on HarmonyOS and excluded because it requires an external TLS network service. It is not counted as passed.
- Conan `test_package` compiled, linked and ran the packaged `glibmm-2.4` and `giomm-2.4` libraries, with 9/9 runtime assertions passing.
- Compilation, exclusion and inability to execute are not counted as passes.
