# minizign 0.1.13 HarmonyOS adaptation notes

## Status

- Current status: OHOS runner smoke passed with `zig/0.16.0.1`; upstream `zig build test` and CLI test_package both pass.
- Issue: not found in local project files or session context; pending.
- Branch: `feat/minizign-0.1.13`
- Worktree: `D:\harmonyos\worktrees\minizign`

## Upstream

- Project: `jedisct1/zig-minisign`
- Tag: `0.1.13`
- Commit from GitHub tag API: `13775486140ffd449bc350af51a2ba86304f0473`
- Source URL: `https://api.github.com/repos/jedisct1/zig-minisign/tarball/refs/tags/0.1.13`
- Source sha256: `7ceabddb5470275a97b3f63bb27e9c54c542b8c908d7792efd51ed9724fd4e0b`

## Build system analysis

- Build system: Zig (`build.zig`, `build.zig.zon`).
- Upstream command: `zig build -Doptimize=ReleaseSmall`.
- Official upstream tests: `zig build test -Doptimize=ReleaseSmall`.
- Additional upstream compatibility test: `test_compatibility.sh`, but it requires an external `minisign` executable and is not integrated into the first recipe pass.

`build.zig.zon` declares:

- `minimum_zig_version = "0.16.0"`
- Zig package dependency `clap`:
  - URL: `git+https://github.com/Hejsil/zig-clap#bf56f229ed5b6c381d90e192234913c6deb3f688`
  - Hash: `clap-0.12.0-oBajB9noAQCFiI2syvjiZf6dENWUBFPWMEzdEPr99ZVx`
  - Adaptation: fetched during Conan `source()` as pinned tarball `https://github.com/Hejsil/zig-clap/archive/bf56f229ed5b6c381d90e192234913c6deb3f688.tar.gz`, sha256 `ef9f9de7278fe07362e0e331423acb7b1b410f30b1327aad03cd3a1775d554dd`, then patched to local `.path = "deps/zig-clap"` to avoid Zig runtime network fetches.

## W0 dependency check

- 2026-07-28 initial check:
  - `conan list 'zig*' -r=ohpcd`: no matching recipe references.
  - `conan list 'clap*' -r=ohpcd`: no matching recipe references.
  - `conan download 'zig/0.16.0' -r=ohpcd --only-recipe`: failed with remote message `system acceleration policy not enabled`.
  - `where.exe zig`: no local Zig executable found.
- 2026-08-08 recheck after Zig publication:
  - `conan download 'zig/0.16.0' -r=ohpcd --only-recipe`: pass, recipe revision `8787d9979dbd764ce731897eab9aef8c`.
  - `conan list 'zig/0.16.0:*' -r=ohpcd`: pass, OHOS/armv8 package `876049f3ae10a4560da345bb02378e03e212bc8c` available.
  - `conan graph info . --user=ohpcd --channel=stable -s:h os=OHOS -s:h os.version=6.0 -s:h arch=armv8 -s:h compiler=clang -s:h compiler.version=15 -s:h compiler.libcxx=libc++ -s:h build_type=Release -s:b os=OHOS -s:b os.version=6.0 -s:b arch=armv8 -s:b compiler=clang -s:b compiler.version=15 -s:b compiler.libcxx=libc++ -s:b build_type=Release`: pass; graph resolves `zig/0.16.0` as a downloadable build requirement from `ohpcd`.
- 2026-08-10 Zig follow-up:
  - `zig/0.16.0.1` is the current downstream tool requirement. It still packages upstream Zig 0.16.0, so upstream `minimum_zig_version = "0.16.0"` remains satisfied.
  - The Zig package now handles OHOS generated runner signing and unit-test terminal execution mode, so minizign no longer skips `zig build test` or retries generated signing in the downstream recipe.
- `conan list 'clap*' -r=ohpcd`: no matching recipe references. This is not a Conan dependency in the final recipe; the fixed Zig package dependency is fetched as source metadata and used locally.

Conclusion: Zig toolchain publication is no longer blocking dependency graph resolution. With `zig/0.16.0.1`, upstream Zig unit tests run on OHOS and the package/test_package pipeline passes.

## Prepared recipe behavior

- `conanfile.py` downloads the pinned tag tarball and verifies sha256 through Conan's `get()`.
- `source()` also downloads the pinned `zig-clap` commit tarball into `deps/zig-clap` and applies `patches/0001-use-zig-clap-tarball-url.patch` so Zig uses a local package path instead of fetching GitHub during `zig build`.
- `build_requirements()` declares `zig/0.16.0.1` as a build tool requirement.
- `build()` runs:
  - `zig version`
  - `zig build -Doptimize=ReleaseSmall`
- `zig build test -Doptimize=ReleaseSmall`
- Zig cache directories are scoped to the Conan build folder via `ZIG_GLOBAL_CACHE_DIR` and `ZIG_LOCAL_CACHE_DIR`.
- On OHOS, `ZIG_OHOS_SIGN_ROOTS` includes the Conan-scoped Zig caches so the `zig/0.16.0.1` wrapper can sign generated build runners. The packaged `zig-out/bin/minizign` is signed when `binary-sign-tool` is available.

## test_package

The consumer test is non-empty and exercises the CLI:

1. `minizign --version`, asserting `minizign 0.1.13`.
2. `minizign -G`, generating an unencrypted key pair.
3. `minizign -S`, signing a generated message.
4. `minizign -V`, verifying the generated signature.

## Local verification

Completed:

- Worktree isolation from Apache Arrow.
- Source metadata and sha256 collection.
- Build system inspection from extracted upstream tag tarball.
- W0 check for Zig and Zig clap availability.
- Recipe and non-empty `test_package` preparation.
- `python -m py_compile conanfile.py test_package/conanfile.py`: pass.
- `conan export . --user=ohpcd --channel=stable`: pass.
- `git diff --check`: pass.
- `conan create . --user=ohpcd --channel=stable -s:h os=OHOS -s:h arch=armv8 -s:h compiler=clang -s:h compiler.version=15 -s:h compiler.libcxx=libc++ -s:h build_type=Release -s:b os=OHOS -s:b arch=armv8 -s:b compiler=clang -s:b compiler.version=15 -s:b compiler.libcxx=libc++ -s:b build_type=Release --build=missing`: blocked at graph resolution because `zig/0.16.0` is unavailable.
- 2026-08-08 `conan graph info` with `os.version=6.0`: pass; `zig/0.16.0` resolves from `ohpcd`.
- 2026-08-10 OHOS runner smoke with `zig/0.16.0.1`:
  - Runner command: `ohos-test-runner.sh --try-lock --user codex --lib minizign --task conan-0.1.13-r11-zig-0.16.0.1 --mode smoke --workdir "$HOME/validation/build_in_harmonyos" -- zsh -lc 'CI_PACKAGES="archives/m/minizign/0.1.13" zsh ci/conan/build_and_test.sh'`
  - Run dir: `/storage/Users/currentUser/ohos-test-runs/codex-minizign-conan-0.1.13-r11-zig-0.16.0.1-20260810-200944-41753`
  - Result: exit code 0.
  - L0/L1/L2/L4/L5: pass; L0k confirms `archives/m/minizign/commands.json` is valid with `type=tool`.
  - Package revision: `minizign/0.1.13#2dd9ef934e546475cd18f2d63a3421a4:6b129b068851896169fae42d399fa922d239ce8a#9c6a08f1facf11ccff6ab03efdcaf4ce`.
  - Upstream test evidence: `zig build test -Doptimize=ReleaseSmall` ran in Conan `build()`; `wasm.test` reports 15/15 tests passed, and the second generated Zig test artifact reports `All 0 tests passed`.
  - test_package evidence: `minizign --version`, unencrypted key generation in a unique temp directory, message signing, and signature verification all executed successfully.
  - PR template rates:
    - `上游测试用例通过率：15/15（100%，按 upstream Zig test assertion 统计；另有 1 个 Zig empty test artifact 为 0/0，不计入分母）`
    - `新增测试用例通过率：1/1（100%，Conan test_package CLI smoke）`

Blocked:

- Windows host `conan create` remains intentionally not run because the resolved `zig/0.16.0.1` binary is OHOS/armv8.
- `test_compatibility.sh` requires `minisign`; defer this optional compatibility test until minisign availability is confirmed.

## Next verification commands

Direct Conan command on OHOS runner:

```sh
cd archives/m/minizign/0.1.13
conan create . --user=ohpcd --channel=stable -pr:h=$HOME/.conan2/profiles/ohos -pr:b=$HOME/.conan2/profiles/ohos --build=missing
```

Single-package CI/shadow CI:

```sh
CI_PACKAGES="archives/m/minizign/0.1.13" zsh ci/conan/build_and_test.sh
```

```sh
/path/to/run-ohos-shadow-ci.sh archives/m/minizign/0.1.13
```

Queue note:

- Package: `archives/m/minizign/0.1.13`
- Resource type: CPU/network, light after Zig is present; network is needed for source-stage `zig-clap` tarball unless mirror/cache already has it.
- Do not run while Apache Arrow or other heavy jobs are occupying the single-device queue.
