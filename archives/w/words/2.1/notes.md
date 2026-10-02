# words 2.1 — HarmonyOS PC port

### 对话 #1 — 2026-09-29

## Scope and source

The selected upstream is Arch Linux `words` 2.1-9. Its package provides international `/usr/share/dict` lists. The recipe downloads eight GNU Aspell dictionary archives over HTTPS and verifies each SHA256 from `conandata.yml`.

The port preserves the nine canonical lists and four compatibility names. It writes aliases as ordinary copied files so consumers do not depend on Unix symlink handling. Arch-only pacman hooks and scripts are not part of this Conan data package.

The package has no Conan runtime or build requirements. Arch uses Aspell's `preunzip` as a host-side data conversion utility; this recipe decodes prezip v1 and v2 in Python instead of depending on an unpublished Aspell Conan package. It converts the upstream ISO-8859-1 entries to UTF-8, removes `/` affix flags, follows the `LC_ALL=C sort -df` ordering, and deduplicates the merged English and German lists as Arch does.

The upstream archives contain nine `Copyright` files, one of which is an empty De-alt placeholder. The package keeps all eight non-empty notices under distinct names, including both German notices.

## Output

The package installs 13 regular files below `share/dict`; `WORDS_DIR` points to that directory for Conan build and run environments.

| Canonical dictionary | Entries |
| --- | ---: |
| american-english | 123,985 |
| british-english | 128,005 |
| catala | 189,057 |
| finnish | 88,328 |
| french | 221,377 |
| italian | 92,034 |
| ngerman | 304,736 |
| ogerman | 76,258 |
| spanish | 56,329 |

The aliases are `usa`, `british`, `catalan`, and `german`. Package metadata records GPL-2.0-only, Ispell, and SCOWL licensing; the upstream notices are retained under `licenses/`.

## Test results

- Conan consumer: passed on the local x86_64 Windows build profile. It checks exact word counts, UTF-8, dictionary ordering, uniqueness, language samples, aliases, and all eight non-empty notices.
- HarmonyOS PC HDC test: passed on the x86_64 emulator. It checked `const.ohos.apiversion` (API 20), staged all dictionary files under `/data/local/tmp/words-2.1`, and ran the checked-in native consumer against American, British, and Spanish lists.
- Native SDK smoke consumer in `test_package/test_words_native.cpp`: cross-compiled for AArch64 and x86_64. ELF `e_machine` values were 183 (AArch64) and 62 (x86_64); the x86_64 consumer ran on the emulator and found `color`, `colour`, and `hola` in their respective lists. The AArch64 binary was not run because the available emulator is x86_64 and no AArch64 device is attached.
- Conan cross-profile consumer: passed with `os=OHOS`, `arch=armv8`, Clang 15 settings, and a Windows x86_64 build profile. This is data-only packaging, so Conan reused the package's cleared, architecture-independent package ID; no target binary is produced by the recipe.
- Repository suite: `python tests/run_all.py` passed 11 of 12 suites. The remaining `test_v1220.py` uses a hard-coded Linux worker Git path unavailable on this Windows host; rerunning that suite with the installed Windows Git executable passed all 33 checks.

The repository `finish` command was attempted. Its clean-verify step found no upstream source tarball (the package is a data-only Conan recipe); the old ConanVerifier G1 also requires `export_sources()` and `apply_conandata_patches()`, which the repository's data-only recipe pattern does not use. W3 then stopped in `setup.sh` with RC=1 before `build_and_test.sh`; this Windows host has no `zsh` and lacks the CI worker's `/data/service/hnp` layout. Direct Conan create/consumer tests, the OHOS cross-profile Conan test, SDK cross-compilation, and HDC emulator tests passed. No `.ci-result.json` was created; the exact finish output is summarized in `reports/test-report.md` and `reports/w3-local-ci.log`.
