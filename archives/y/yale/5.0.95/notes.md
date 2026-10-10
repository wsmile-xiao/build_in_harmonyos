# Yale 5.0.95 HarmonyOS data package

## Scope and upstream data

`yale/5.0.95` packages the Yale Bright Star Catalog, 5th Revised Edition (preliminary), as original data resources. The Debian version identifies the data-package release; the catalogue itself is the 1991 BSC5 edition. The official CDS V/50 archive provides `catalog.gz`, `notes.gz`, and `ReadMe` over HTTPS. The CDS ReadMe identifies 9,110 catalogue rows and 9,190 remark rows, and documents the fixed-width columns.

The CDS copy records a few changes made in 1993 and 1995 with Wayne H. Warren Jr.'s agreement. Its `catalog.gz` is 573,921 bytes and matches the published SHA256 for the Harvard `ybsc5.gz` payload. All three CDS source files were downloaded with normal HTTPS certificate validation and their SHA256 values are pinned in `conandata.yml`. The installed files remain compressed and byte-for-byte unchanged.

## Attribution and data handling

The data are copyrighted by Dorrit Hoffleit and Wayne H. Warren Jr. Historical distribution guidance records permission to redistribute the original ADC data with acknowledgment of the ADC and authors, and prohibits altered data. The package preserves the official CDS `ReadMe` and adds explicit attribution in the software README. The catalogue data are not covered by the GPL license used for the historical packaging scripts and documentation.

## Conan package

This is a pure data resource: it has no compilation stage, library, header, executable, or runtime package dependency. `package()` copies the three validated source files into `share/yale/`. The package ID is cleared because the resource bytes do not vary by architecture, compiler, or build type. Conan exposes the installed resource directory as `YALE_BSC5_DIR`.

## Upstream test inventory (R51)

The official CDS V/50 ReadMe file summary lists only the ReadMe, catalogue, and remarks data files. The distribution contains no source build system, test directory, test registration, or upstream functional test command; upstream functional test count is zero. The consumer test therefore verifies the installed resources directly rather than claiming an upstream test suite.

## Consumer test

`test_package/test_data.py` uses Python 3 standard library only. It checks the exact installed file set, sizes, and SHA256; streams and parses all 9,110 fixed-width catalogue records and all 9,190 remarks; validates HR numbering, J2000 coordinate fields, categories, and the HR 2491 Sirius record; and reads the upstream field documentation. The HarmonyOS-only invocation also confirms `platform.system()` is `HarmonyOS` and `platform.machine()` is `aarch64`, then repeats full catalogue and remarks consumption from Conan's `YALE_BSC5_DIR`.

## Source checksums

| File | Size | SHA256 |
|---|---:|---|
| `catalog.gz` | 573,921 | `3dc44b1e90be8fbe5bcc7656032560f51275f985c7e3f783c9028e1838ec7bed` |
| `notes.gz` | 161,634 | `d489d8ceaead65b0af8bce36f2421886782bbe953ecf76b08bc3fd4b84df1405` |
| `ReadMe` | 11,571 | `44fd9c73e2eecad0beb47bdfa3f01c60fd43f93d6964198e31fcd48732de5b33` |

## 发现与知识

- ✅ [ref: E255] Conan 2.29.1 的 `package_type` 枚举不接受 `none`；纯数据资源使用受支持的 `unknown`，并在 HarmonyOS 设备上通过 Conan create 验证。

## Validation status

- Host-side consumer script against the three CDS HTTPS downloads: 4/4 named tests passed.
- HarmonyOS 6.0 aarch64 Conan create/test: 5/5 named tests passed; the platform-specific case consumed and parsed all installed catalog and notes rows.
- Repository aarch64-profile local CI (W3): passed; Conan test package consumed installed resources and passed 4/4 named tests.
- Conan verifier: G1, G2, and G3 passed for the final recipe.
- `ohc-run.py finish yale 5.0.95 built`: W3 passed and generated `.ci-result.json`. The overall finish was partial because W2 compared against the older `origin/main` ref instead of the branch's `upstream/main` baseline, W5 found existing incomplete knowledge entries elsewhere in the repository, and the repository SUMMARY generator raised `'str' object has no attribute 'append'`. No PR was requested, so submit-readiness checks were not completed.
---

**编译结束**: 2026-10-04 22:24
**最终状态**: built
