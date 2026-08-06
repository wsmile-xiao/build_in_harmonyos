# tektoncd-cli 0.45.0.1 HarmonyOS PC notes

## Adaptation summary

- Upstream source: official GitHub tag `v0.45.0`.
- Build system: Go module command under `./cmd/tkn`.
- OHOS strategy: build a pure Go `linux/arm64` executable with `CGO_ENABLED=0`.
- The recipe keeps `GOCACHE`, `GOMODCACHE`, `GOPATH`, and `TMPDIR` inside the Conan build folder.

## Validation

- `python -m py_compile` passed for the recipe and test package.
- `git diff --check` passed.
- Local CI simulation (`ci/conan/build_and_test.sh`, profile `ohos-aarch64`) passed on aarch64 Linux: L0 quality gate, L1 test_package execution, L1e negative test, L2 smoke test (`tkn --help`), L4 security scan, L5 artifact check — all passed.
- The test package executes the packaged `tkn` binary and runs 12 offline assertions (`test_tkn.py`): executable presence, main help identification and subcommand listing, `version` output and version number `0.45.0`, `pipeline --help`, and `completion bash`. Pass rate: 12/12 (100%).
- Official OHOS CI remains authoritative for target binary execution.
