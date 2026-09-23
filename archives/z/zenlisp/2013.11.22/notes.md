# zenlisp 2013.11.22 pre-adaptation notes

## Source

- Upstream: https://github.com/barak/zenlisp
- Tag: `upstream/2013.11.22`
- Commit: `9ae13c8b5ecd5e4d1167cf446532208ab2ee97b0`
- Source archive: `https://github.com/barak/zenlisp/archive/9ae13c8b5ecd5e4d1167cf446532208ab2ee97b0.tar.gz`
- SHA256: `5285107e98516da16a9fe457a22ecacb9eb758d47b12057916eea0a2cdea49db`
- License: BSD-2-Clause-style permissive license (the upstream text grants unrestricted copying and modification and includes a BSD-style disclaimer).

## W0 dependency result

- Runtime dependencies: none.
- Build dependencies: the C compiler and the native shell supplied by the HarmonyOS Conan environment.
- Test dependencies: none.
- Dependency split: not required.

## W1 source and build analysis

- Language: ANSI C89 interpreter plus zenlisp source libraries.
- Upstream build system: a small Makefile.
- Build products: `zl` ELF interpreter and a generated `zenlisp` default image.
- Runtime data: root `.l` libraries, `src/*/*.l` examples, `zl.1`, `zenlisp.txt`, and `LICENSE`.
- Upstream test: `test.l` compared against `test.OK`; the Makefile's BSD-specific `sed -i ''` normalization is reproduced in Python inside the recipe.
- External service or network tests: none.

## HarmonyOS adaptation

The source uses `strdup()` but does not define a feature-test macro. The HarmonyOS Native SDK exposes that declaration with `-D_GNU_SOURCE`, matching knowledge entry E032. The recipe also applies `0001-relocatable-default-image.patch`, which lets `ZENLISP_IMAGE` override the compiled fallback path. `package_info()` supplies both `ZENLISP_IMAGE` and `ZENSRC` from the actual Conan package folder.

The upstream `install` target passes `-o bin -g bin` and calls `strip`; package() therefore copies the known runtime files directly and does not invoke that target.

## Path B knowledge contribution

This package is submitted as **Path A plus a Path B knowledge contribution candidate**. The
reusable contribution is the complete native Conan closure for a tool whose build must execute
itself to generate a runtime image:

- compile and sign the target interpreter before the first build-time execution;
- generate the image on the OHOS target rather than importing a host-generated image;
- relocate the image and source-library paths from upstream `/usr/local` assumptions to the
  installed Conan `package_folder`;
- keep the full upstream regression and an installed consumer test in separate evidence layers;
- record the non-applicable `--version/--help` smoke result as L2 skip instead of treating it as
  either a failure or a pass.

The paired reusable draft is:
`knowledge/drafts/DRAFT-zenlisp-native-image-conan-ohos.md` and
`knowledge/drafts/DRAFT-zenlisp-native-image-conan-ohos.kv`.

## Verification

- Source archive downloaded locally and SHA256 verified.
- A direct SDK compile to `aarch64-linux-ohos` succeeded with warnings only after adding `-D_GNU_SOURCE`.
- Native execution, default image generation, upstream regression comparison, Conan package creation, and `test_package` were completed by the HarmonyOS Shadow CI run below.
- No issue number was found or used; the handoff remains issue-pending per the request.

## Test execution and pass-rate evidence

| Test layer | Discovered | Executed | Passed | Failed | Pass rate | Evidence |
|---|---:|---:|---:|---:|---:|---|
| Upstream regression | 633 | 633 | 633 | 0 | 100% | `test.l` executed by native `zl`, output compared with `test.OK` |
| Installed consumer test | 7 | 7 | 7 | 0 | 100% | `test_package/test_zenlisp.sh`, exit code 0 |
| Combined executed checks | 640 | 640 | 640 | 0 | 100% | Shadow CI build #46893 |

The upstream suite is not counted as modified: the recipe only normalizes dynamic error
counters before comparison. The seven consumer assertions are additional post-install
checks for the executable, generated image, source-library loading, arithmetic, and license
output.

## 2026-09-14 HarmonyOS Shadow CI

- Device environment: HarmonyOS aarch64, clang 15, Conan 2.29.1, profile `ohos-aarch64`.
- Isolated run: `20260914T002209Z-dfbfd1ac80-20807`.
- `conan create` completed with exit code 0.
- The patch was applied by the device `patch -p1` command, the binary was signed by `binary-sign-tool`, and the default image was generated successfully.
- The official upstream regression comparison executed and passed: 633/633 expected cases.
- `test_package` executed and passed all 7 assertions, including installed binary, image, source library loading, arithmetic, and license output.
- Shadow summary: L0 pass, L1 pass, L2 skip because `zl` has no `--version`/`--help`, L4 pass, L5 pass.
- The software-level `archives/z/zenlisp/commands.json` declares the CLI tool and its
  `2013.11.22` version reference, satisfying the R38 metadata gate.

## Conan package artifact

- The package artifact was exported from the successful isolated Shadow CI Conan package folder.
- It contains `bin/zl`, `share/zenlisp/zenlisp`, the packaged `.l` runtime libraries,
  `licenses/LICENSE`, `conaninfo.txt`, and `conanmanifest.txt`.
- Artifact: `packaging/zenlisp-2013.11.22-ohos-aarch64-conan-package.tar.gz`
- SHA256: `49477901A9FB2284CF7721B68B446D60D168550FB964E7EB72C4DE3089B143D8`
- This is a Conan package export for submission evidence, not a hand-written installer pipeline.

## Patch compatibility note

- The first Shadow CI attempt failed inside Conan's `conan.tools.files.patch()` parser with `source/target file does not exist`.
- The same unified diff applied cleanly with the device Toybox `patch -p1`; the recipe now invokes that command explicitly through the configured native shell.
- The second Shadow CI run passed after this minimal recipe change.

## Reproduction command

```sh
conan create archives/z/zenlisp/2013.11.22 --build=missing
```

Then run the isolated Shadow job and record any future signing or HMDFS regression. Do not put device IP addresses or private-key paths in repository files.

## 最终状态

- 状态：`built`
- 本机前置适配、OHOS aarch64 Shadow CI、Conan 构建、上游回归和安装后 `test_package` 均已完成。
- 路径 B 草稿已补充并通过草稿预审；正式知识条目编号及 B 类认定由维护者/评审决定。
- 编译结束：2026-09-14
