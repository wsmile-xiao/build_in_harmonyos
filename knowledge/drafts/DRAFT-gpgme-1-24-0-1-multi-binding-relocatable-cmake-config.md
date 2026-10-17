**DRAFT-gpgme-1-24-0-1-multi-binding-relocatable-cmake-config - GPGME multi-binding package exports relocatable CMake configs after DESTDIR installation**

When GPGME is installed through `DESTDIR`, the upstream CMake metadata retains `/lib` and `/include`. The package must replace that metadata with three package-local configs whose imported locations are computed from `CMAKE_CURRENT_LIST_DIR`, while retaining the `gpgme -> Gpgmepp -> QGpgmeQt6` dependency chain. This is a dependency-library knowledge candidate, not an application workaround.

**Identity and current conclusion**

| Field | Value |
|---|---|
| Draft ID | `DRAFT-gpgme-1-24-0-1-multi-binding-relocatable-cmake-config` |
| Structured file | `knowledge/drafts/DRAFT-gpgme-1-24-0-1-multi-binding-relocatable-cmake-config.kv` |
| Current status | Existing evidence pending review |
| Suggested destination | Supplement to existing patterns |
| Contributor | `zxyAtom` |
| Source PR | #7424, `feat/gpgme-1.24.0.1`, source baseline `8787bcfc7a7878e530138e2795b3513d8965c12c` |
| Extraction method | Existing ordinary PR upgrade |
| Delivery | In-place upgrade of PR #7424 |
| Package | `gpgme/1.24.0.1`; upstream `gpgme-1.24.0` |
| Last updated | 2026-09-06 |

The static package contract is verified in the recipe: all three generated configs derive `_GPGME_PREFIX` from their own config-file directory, and the test consumer discovers, links, and loads all three bindings. An OHOS device rerun and raw CI-log-to-HEAD binding remain unproven in this extraction pass.

**Evidence from the original PR**

| Original fact | Source location | Reusable mechanism | This extraction adds |
|---|---|---|---|
| Installed upstream configs retain absolute `/lib` and `/include` paths after `DESTDIR`. | `conanfile.py`, `_write_relocatable_cmake_configs()` | Install package-local imported targets and calculate prefix relative to each config file. | One multi-binding contract with explicit boundaries. |
| C, C++, and Qt6 bindings are all published. | `conanfile.py`, `package_info()` | Preserve the target chain `gpgme::gpgme`, `Gpgmepp`, `QGpgmeQt6`. | Consumer-level verification mapping. |
| Consumer configures, links, and executes all three bindings. | `test_package/CMakeLists.txt`, `test_gpgme.cpp`, `test_package/conanfile.py` | Validate discovery plus runtime symbol loading, not only library production. | Separates historical result from a new run. |

The original implementation also repairs dependency config scripts and `.pc`/`.la` metadata. That part remains covered by E433/E435; this draft only adds the distinct installed CMake export contract.

**Trigger, cause, and minimal repair**

Applicable input is an OHOS aarch64 Conan package built with `--enable-languages=cpp,qt6`, `libgpg-error/1.55`, `libassuan/3.0.2`, and `qtbase-sql-dbus/6.11.1`. The package's own notes state that upstream configs point at `/lib` and `/include` after `DESTDIR` installation.

1. Create `lib/cmake/gpgme/gpgmeConfig.cmake`, `lib/cmake/Gpgmepp/GpgmeppConfig.cmake`, and `lib/cmake/QGpgmeQt6/QGpgmeQt6Config.cmake` during packaging.
2. In each file, compute the prefix with `get_filename_component(... "${CMAKE_CURRENT_LIST_DIR}/../../.." ABSOLUTE)`.
3. Export imported-library locations and include paths from that prefix, and preserve the dependency chain: core depends on `libassuan` and `libgpg-error`; C++ depends on core; Qt6 depends on C++ and `Qt6::Core`.

Do not hardcode a Conan cache, build directory, or `DESTDIR` prefix in the imported targets. That turns a relocatable installed package back into a build-machine artifact.

**Verification matrix**

| ID | Type | Input and entry point | Result | Evidence |
|---|---|---|---|---|
| EVID-01 | static | Source baseline `8787bcfc`; `_write_relocatable_cmake_configs()` | Three configs use `CMAKE_CURRENT_LIST_DIR` and define the expected target chain. | Recipe source captured in `archives/g/gpgme/1.24.0.1/conanfile.py`. |
| EVID-02 | static | `test_package/CMakeLists.txt` and `test_gpgme.cpp` | Consumer finds all three configs, links all three targets, calls `gpgme_check_version`, initializes GpgME++, and resolves `QGpgME::openpgp`. | Test sources in the same package directory. |
| EVID-03 | historical | `notes.md` and `manifest.yaml` describe `conan create` consumer execution. | Historical claim: CTest `1/1` and direct three-binding version output. Raw CI log has not been rebound to the source baseline in this pass. | `notes.md`; fallback-runner path recorded there. |

**Test inventory**

| Scope | Unit | Inventory | Pass | Fail | Skip | Not run | Basis |
|---|---:|---:|---:|---:|---:|---:|---|
| Upstream GPGME suite | tests | 45 | 0 | 0 | 0 | 45 | The recipe builds only `src`, `lang/cpp/src`, and `lang/qt/src`; upstream suite requires a real GnuPG runtime not published on OHOS PC. |
| Installed-package consumer | CTest case | 1 | 0 | 0 | 0 | 1 | Historical `1/1` is recorded, but raw log and current HEAD binding require review before counting it as this extraction's executed result. |
| Generated config contract | config files | 3 | 3 | 0 | 0 | 0 | Static inspection of the three generated config bodies. |

No overall rate is claimed: these rows use different units. Build success alone cannot demonstrate actual cryptographic operations, GnuPG-agent integration, or relocatability after copying a complete package to a different prefix.

**Boundary and relationship**

| Reusable premise | Verified here | Not verified here |
|---|---|---|
| Three installed libraries have CMake consumer targets. | gpgme 1.24.0.1's generated config structure and consumer source. | Other GPGME versions or target platforms. |
| Prefix is derived from config location. | Source-level relative path construction. | Physical package move followed by target execution. |
| Dependency config inputs need repair. | Existing recipe contains overrides. | General replacement for E433/E435. |

Existing entries E433 and E435 address dependency config-script execution and metadata overlays. The incremental knowledge here is the package-exported, three-binding CMake surface after installation. A future device rerun should copy the installed package to a second prefix and run the same consumer against each config before this becomes an accepted general rule.

**Source index and handoff**

| Material | Location | Role |
|---|---|---|
| Upstream source | `https://www.gnupg.org/ftp/gcrypt/gpgme/gpgme-1.24.0.tar.bz2` | SHA256 `61e3a6ad89323fecfaff176bc1728fb8c3312f2faa83424d9d5077ba20f5f7da` |
| Implementation | `archives/g/gpgme/1.24.0.1/conanfile.py` | Config generation and Conan component metadata |
| Consumer | `archives/g/gpgme/1.24.0.1/test_package/` | CMake discovery, link, CTest, and direct smoke program |
| Evidence report | `archives/g/gpgme/1.24.0.1/reports/knowledge-evidence.md` | Source and evidence-boundary index |

Final recommendation: support in-place knowledge-base upgrade after the remote author, current HEAD, and raw CI log are reread. The remaining concrete task is a current OHOS `conan create` plus a relocation rerun; neither should be inferred from this static extraction.
