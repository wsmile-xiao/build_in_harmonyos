# astc-encoder 5.3.0 adaptation notes

## Scope

- Issue: **待补** (项目内未找到明确 issue 编号)
- Worktree: `D:\harmonyos\worktrees\astc-encoder`
- Branch: `feat/astc-encoder-5.3.0`
- Adaptation path: `archives/a/astc-encoder/5.3.0`

## W0 Dependency Check

- astc-encoder is fully self-contained with no external library dependencies.
- The only submodule is GoogleTest (`Source/GoogleTest`), used only when `ASTCENC_UNITTEST=ON`.
- GoogleTest submodule is not reliably available in CI environments, so unit tests are skipped in the recipe.
- No missing mandatory dependencies; W0 passes.

## Source And Build System

- Source URL: `https://github.com/ARM-software/astc-encoder/archive/refs/tags/5.3.0.tar.gz`
- SHA256: `6bd248f460b90576f90a5499c0f6b8d785b3af3837bcab82607d9a3b5bba77e2`
  - Computed on OHOS device via Python urllib (36,162,057 bytes)
- Build system: CMake (minimum 3.15), C++14 standard
- License: Apache-2.0
- Patches: none

## ISA Selection

On OHOS/aarch64:
- `ASTCENC_ISA_NEON=ON` — use ARM NEON SIMD
- All x86 ISA options (SSE2, SSE41, AVX2) explicitly OFF
- `ASTCENC_NATIVE=OFF` — do not auto-detect

## Recipe Strategy

- Static library by default (`ASTCENC_SHAREDLIB=OFF`)
- CLI tool enabled (`ASTCENC_CLI=ON`)
- Unit tests disabled (`ASTCENC_UNITTEST=OFF`) — GoogleTest submodule not available
- Warnings-as-errors disabled (`ASTCENC_WERROR=OFF`) — clang 15 differences
- Floating point invariance enabled (`ASTCENC_INVARIANCE=ON`)
- Compiler: `clang-15` directly (not the shell wrapper script, due to HarmonyOS execution policy)

## OHOS-specific Adaptation Notes

### clang-15 vs clang wrapper

The device's `$HOME/usr/local/bin/clang` is a shell script that wraps `clang-15`. Due to
HarmonyOS execution policy (file owned by different uid), the wrapper script cannot be
executed directly. Using `clang-15` (the real binary) as `CMAKE_C_COMPILER` works.

### Sysroot

`CMAKE_SYSROOT` must be set to `$HOME/usr/local/sysroot` for system headers.
The sysroot contains OHOS system headers (kernel, NDK, etc.) but NOT libc++.

### libc++ Linking

libc++ libraries are at `$HOME/usr/local/lib/aarch64-linux-ohos/` (NOT in the sysroot).
clang-15 with `-fuse-ld=lld` does NOT auto-link libc++. Explicit flags required:
```
-L<toolchain>/lib/aarch64-linux-ohos -fuse-ld=lld -lc++ -lc++abi
```

### Upstream CMake Install Gap

Upstream CMake only installs the CLI binary (`astcenc-neon`). The static library and
public header are NOT installed. The Conan recipe's `package()` method manually copies:
- `libastcenc-neon-static.a` → `lib/`
- `astcenc.h` → `include/`
- `astcenc-neon` → `bin/`

## Products

- `lib/libastcenc-neon-static.a` — static library (375,962 bytes)
- `include/astcenc.h` — public header
- `bin/astcenc-neon` — CLI compression tool (675,160 bytes)

## Test Strategy

- Upstream GoogleTest unit tests are recorded in `test_package/MANIFEST.yml` but not
  integrated into `build()` due to GoogleTest submodule dependency.
- `test_package/test_astcenc.cpp` performs a consumer smoke test: version check, config
  init, context alloc, compress+decompress round-trip on a 4x4 RGBA image (5 assertions).

## Device Build Verification

Isolated job on OHOS device via SSH (frp-tip.com:56267):

```text
Job: ohos-users/codex-astc-encoder/astc-encoder-5.3.0
CONAN_HOME: .../conan-home
Compiler: clang-15 (direct, not shell wrapper)
Sysroot: /storage/Users/currentUser/usr/local/sysroot
```

CMake build results:
- `libastcenc-neon-static.a`: 375,962 bytes ✅
- `astcenc-neon` CLI: 675,160 bytes ✅ (link succeeded with -lc++ -lc++abi)
- Compile: 22 C++ source files, 0 errors
- Link: CLI linked successfully with explicit libc++ flags

Known issue: Direct binary execution on this device is blocked by HarmonyOS permission
policy (uid mismatch). The binary will work in CI environments with matching uid.

## Known Issues and Risks

1. **Issue 待补**: No issue number found in the project; to be filed separately.
2. **GitHub download intermittent**: GitHub is intermittently unreachable from OHOS devices.
   Source was downloaded via Python urllib with extended timeout.
3. **GoogleTest submodule**: Upstream tests need `git submodule update --init` to fetch
   GoogleTest. Not available in CI without git network access.
4. **Binary execution permissions**: Direct execution may fail on devices with uid mismatch;
   CI environment handles this differently.

## Next Commands

Single-package shadow CI, when the device or shadow runner is available:

```sh
CI_PACKAGES="archives/a/astc-encoder/5.3.0" zsh ci/conan/build_and_test.sh
```

Alternative shadow runner:

```sh
/path/to/run-ohos-shadow-ci.sh archives/a/astc-encoder/5.3.0
```

Manual Conan verification on an OHOS worker with matching uid:

```sh
cd archives/a/astc-encoder/5.3.0
conan create . --user=ohpcd --channel=stable \
  -pr:h=$HOME/.conan2/profiles/ohos-aarch64 \
  -pr:b=$HOME/.conan2/profiles/ohos-aarch64 \
  --build=missing
```
