# tektoncd-cli 0.45.0 HarmonyOS PC notes

## Adaptation summary

- Upstream source: official GitHub tag `v0.45.0`.
- Build system: Go module command under `./cmd/tkn`.
- OHOS strategy: build a pure Go `linux/arm64` executable with `CGO_ENABLED=0`.
- The recipe keeps `GOCACHE`, `GOMODCACHE`, `GOPATH`, and `TMPDIR` inside the Conan build folder.

## Validation

- `python -m py_compile` passed for the recipe and test package.
- `git diff --check` passed.
- Local `conan create` was not run because this Windows workspace does not provide the competition OHOS Conan/Go toolchain.
- The test package checks `tkn --help` and `tkn version` when the target binary can be executed.
