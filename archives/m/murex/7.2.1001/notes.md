# murex 7.2.1001 HarmonyOS PC notes

## Adaptation summary

- Upstream source: official GitHub tag `v7.2.1001`.
- Build system: Go module, single `murex` command from the repository root.
- OHOS strategy: build a pure Go `linux/arm64` executable with `CGO_ENABLED=0`.
- The recipe keeps the fallback Go toolchain, `GOCACHE`, `GOMODCACHE`, `GOPATH`, `TMPDIR`, `GOTMPDIR`, and the Go linker `-o` target under an external OHOS hmfs work root such as `/data/storage/el2/base/cache/conan-go-build/murex-7.2.1001`, then copies the final binary back to the Conan build folder. Keeping this tree outside the murex module prevents `go test ./...` from accidentally discovering Go distribution fixtures under `go/test`, and avoids the HMDFS mmap restriction that makes Go's linker fail with `mapping output file failed: permission denied`.
- The fallback Go toolchain is chmod-normalized recursively after extraction so the toolchain root directories are traversable and `go/bin/go` plus bundled host tools remain executable on OHOS/HMDFS workers.

## Validation

- `python -m py_compile` passed for the recipe and test package.
- `git diff --check` passed.
- CI #13020 still failed with `PermissionError: [Errno 13] Permission denied` for `go/bin/go`; the recipe now normalizes the whole fallback toolchain tree, including parent/root directories, and verifies `go/bin/go` is executable before invoking `go build`.
- CI #14110 then reached the Go link stage but failed on HMDFS with `link: mapping output file failed: permission denied`; the recipe now moves Go caches, temporary directories, and linker output to an hmfs work root before copying the binary back.
- CI #15198 then failed because `go test ./...` also scanned `build-release/go-toolchain/go/test` and executed Go distribution fixtures with relative imports; the fallback Go toolchain now lives outside the murex module tree.
- CI #15415 confirmed that the OHOS `go test -exec` wrapper signs and runs the generated test binaries. The suite reached a single failure, `TestAspellInstalled`, whose upstream implementation only checks whether the optional `aspell` executable exists in `PATH`.
- The official OHOS Worker does not provide `aspell`, and this application package does not bundle optional external commands. For OHOS only, the recipe now sets upstream's documented-in-source `MUREX_TEST_NO_EXEC_DEPS` switch. This leaves every Go test package enabled while disabling only external-command presence checks.
- The recipe now runs the upstream `go test ./...` suite before `go build`; upstream tag `v7.2.1001` contains 326 `*_test.go` files and 876 `func Test...` cases.
- Local `conan create` was not run because this Windows workspace does not provide the competition OHOS Conan/Go toolchain.
- The test package runs `murex -c "echo ohpcd"` and `murex -version` when the target binary can be executed.

