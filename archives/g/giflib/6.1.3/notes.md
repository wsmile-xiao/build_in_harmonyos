# giflib 6.1.3 adaptation notes

## Scope

- This is dependency Issue #1315 for the GraalVM task #1085.
- The adaptation uses Path A for the Conan recipe and HarmonyOS portability
  fixes, plus Path B for the reusable E242 error-lifetime test pattern.
- E242 remains a paired `draft: true` KV/Markdown entry under
  `knowledge/graph/draft` and is submitted with this software. No formal
  graph, document index, operation guide, or `SUMMARY.md` is modified.

## Source and build

The official SourceForge release archive has SHA256
`b65b66b99f0424b93525f987386f22fc5efb9da2bfc92ad4a532249aaffbab0e`.
giflib uses a direct Makefile build and has no third-party Conan dependency.
The recipe obtains `clang` and `llvm-ar` from Conan configuration, builds the
library and fourteen upstream utilities with `-fPIC`, and runs the upstream
regression suite before packaging.

On HarmonyOS, every utility is stripped of its previous `.codesign` section
and self-signed before the regression suite runs. The shared library is also
re-signed before loading and packaging. A shared package contains three real,
byte-identical files named `libgif.so`, `libgif.so.7`, and
`libgif.so.7.2.0`; this avoids HMDFS symlink creation while preserving the
upstream `libgif.so.7` SONAME. Static mode packages only `libgif.a`.

## 遇到的问题与解决方案

| 问题 | 根因 | 解决方案 |
|---|---|---|
| `getversion` and test helpers cannot be executed directly | The target requires scripts to run through an explicit POSIX shell | Patch the authoritative Makefiles to invoke helpers with `SHELL` |
| GNU `head --bytes=-20` is unavailable | The target userland does not implement that GNU-only option | Compute the byte count with `wc -c` and truncate through POSIX `dd` |
| `tapdiffer` writes under `/tmp` | The target `/tmp` location is not a reliable caller-owned workspace | Build the temporary path under `TMPDIR` and clean it with a trap |
| Built ELF files need a valid target signature before execution | HarmonyOS enforces ELF code signatures | Re-sign utilities, the shared library, and the consumer executable before running them |
| Operation failures were easy to diagnose through the wrong error variable | Open/close use out-parameters while live operations store errors in `GifFileType::Error` | Snapshot the live-handle error before close and use separate open/close variables |

All three source patches were generated on the HarmonyOS target with POSIX
`refresh-patch --auto`. The full patch set passes local `git apply --check`,
GNU patch 2.7.6 `--fuzz=0`, target dry-run, and Conan patch-ng replay.

## 依赖版本

- Third-party Conan runtime dependencies: none.
- Build and test tools: clang 15.0.4, llvm-ar, llvm-objcopy,
  binary-sign-tool, Make, CMake, Python 3.12.9, and Conan 2.29.1.
- The W0 target probe used `--build=never` and confirmed that
  `giflib/6.1.3` is not yet available from the `ohpcd` remote.

## 验证结果

The final input bundle SHA256 is
`3eef2189a6431d9c37239975fafffd6bfa27ed642a5116a82aae30046b358edd`.
It was copied into a previously absent target directory and built with a new
Conan home. Both shared and static modes passed:

- 51/51 upstream TAP regression entries;
- 3/3 separately launched public-API consumer workflows;
- 54/54 logical cases in total, with 76 checks;
- zero failure and zero skip;
- AArch64 shared output with SONAME `libgif.so.7` and one `.codesign` section;
- three byte-identical, non-symlink shared package files and one static archive.

Shared and static are packaging-mode reruns of the same logical cases and are
not added together. Signing commands and artifact inspections are evidence,
not extra software test cases.

The final shared log has 296 physical lines and SHA256
`101fe1299918effdaeed589dfcb1465c797c1c189245291f27c592334d0f03de`.
The final static log has 284 physical lines and SHA256
`bf37dfe59f39380ed1c010d738cdb4253cf62ee2dc3172f3af2778315d4b5086`.

## 源码修改

- `Makefile`: run `getversion` through the selected shell.
- `tests/makefile`: use the selected shell for helpers and replace GNU-only
  truncation with `wc` plus `dd`.
- `tests/tapdiffer`: allocate its diff file under `TMPDIR`.
- No codec algorithm, public header, ABI version, fixture content, or test
  expected output is changed.

## Knowledge decision

The current `origin/main` graph, documentation, and operation guides contain
no equivalent entry for APIs whose open/close error out-parameters differ
from live-handle operation errors. E242 records the bounded pattern: confirm
the documented ownership, snapshot the handle error before cleanup, and use
separate deterministic consumer processes for success and failure paths.

---

**编译结束**: 2026-07-20 12:41 +08:00
**最终状态**: built
