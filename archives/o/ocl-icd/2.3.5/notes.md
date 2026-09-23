# ocl-icd 2.3.5 适配笔记

## 编译环境

- 构建系统: autotools（configure.ac + Makefile.am，需 autoreconf 自举）
- 编译日期: 2026-09-07
- 编译器: clang/clang++
- 状态: built（首轮未提交工作树，待 HMBS 真机预检）

## 上游信息

- 名称：ocl-icd（OpenCL ICD Loader，厂商 ICD 加载器的自由软件实现）
- 版本：2.3.5（上游 tag v2.3.5，commit 3e1155f，本次新增 OpenCL 3.1 支持、loader 反初始化与 OCL_ICD_FILENAMES 环境变量）
- 仓库：https://github.com/OCL-dev/ocl-icd
- 许可证：BSD-2-Clause
- 源码包：https://github.com/OCL-dev/ocl-icd/archive/refs/tags/v2.3.5.tar.gz（117902 字节，sha256 见 conandata.yml）
- 与 Khronos 官方 opencl-icd-loader 的区别：OCL-dev/ocl-icd 采用数据库驱动生成（icd_generator.rb + ocl_interface.yaml），自带 khronos-headers 副本，无需外部 opencl-headers 依赖；产物同样为 libOpenCL。

## 上游测试清点（R51 第一步）

| 来源 | 用例数 | 说明 |
|------|--------|------|
| tests/testsuite-standard.at | 15 | AT_SETUP：vendors 目录/文件枚举、OPENCL_VENDOR_PATH、dummy ICD、layer、OCL_ICD_FILENAMES |
| tests/testsuite-default-platform.at | 16 | AT_SETUP：默认平台选择、按 GPU/CPU/device 排序 |
| tests/testsuite-workaround.at | 3 | AT_SETUP：Intel bug workaround（含 1 个预期失败用例 ocl_test 返回码 3） |
| check_PROGRAMS ocl_test / ocl_test_icdl | 2 个二进制 | 被 autotest 套件调用的自检程序 |
| **合计** | **34** | autotest 用例总数；驱动命令 `make check`，结果汇总于 tests/testsuite.log |

## 编译步骤

1. `get()` 解包官方 tag 归档。
2. `autoreconf`（tool_requires automake/1.18 + libtool/2.5.4.1，与 zbar 同模式）生成 configure。
3. `sed s/umask 077/umask 022/ configure`（E011：HMDFS 继承 umask 077）。
4. `configure --enable-shared --disable-static --build=aarch64-unknown-linux-ohos --host=aarch64-unknown-linux-ohos`
   （E007：自带 config.guess 无法识别 HarmonyOS；config.sub 可规范化 linux-ohos，故显式三元组走原生模式）。
5. `make -j1`（R9 精要：HMDFS 下单作业；附 ACLOCAL/AUTOMAKE/AUTOHEADER=true 防时间戳回流）。
6. `make check`（上游测试，失败即中断构建），随后解析 tests/testsuite.log 输出 HMBS_UPSTREAM_TEST_RESULT 标记。
7. `make install`，删除 lib/*.la，拷贝 COPYING 至 licenses。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | GitHub 归档无 configure | 上游只提交 configure.ac，需自举 | tool_requires automake/1.18 + libtool/2.5.4.1，build() 内 autoreconf |
| 2 | config.guess 无法识别 HarmonyOS | 自带 config.guess 早于 HarmonyOS | 显式 --build/--host=aarch64-unknown-linux-ohos（e2fsprogs/zbar 同法） |
| 3 | autoreconf 产物 umask 077 | HMDFS 权限语义（E011） | 改写 configure 内 umask 为 022 |
| 4 | 构建期 ruby 依赖 | icd_generator.rb 生成 dispatch 表 | 真机系统自带 ruby（buildessential 已实证 ruby 3.4.5），无需 tool_requires |
| 5 | 文档工具缺失 | asciidoc/a2x/xmlto 在 CI 无 | configure 自动降级 gen_doc=0，无需处理 |

## 源码修改

无补丁（patches_applied 为空）。POSIX 兼容源码，无需 __OHOS__ 守卫（R8 干净）。

## 依赖版本

- 运行时依赖：无（构建使用源码自带 khronos-headers 副本）。
- 构建工具：automake/1.18、libtool/2.5.4.1（tool_requires，制品仓已有，与 zbar 同版本）。
- 系统工具：ruby（真机自带）、clang 15、make。
- 消费者测试头文件：opencl-headers/2026.05.29（仅 test_package 引用，主配方无 requires）。

## 验证结果

首轮为未提交工作树，待 HMBS 后台真机预检（conan create + make check 34 用例 + test_package 1 用例）。
预检日志中的 conan create 输出将作为 PR 正文通过率的唯一依据，届时回填。

```bash
# 真机将执行（HMBS 后台调度，本机不运行 conan）：
# conan create archives/o/ocl-icd/2.3.5 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
# 期望标记：
# HMBS_UPSTREAM_TEST_RESULT={"status":"passed","framework":"autotest","command":"make check","discovered":34,...}
# HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":true,...,"discovered":1,"passedCount":1}
```

## 交付物

| 文件 | 说明 |
|------|------|
| lib/libOpenCL.so | ICD 加载器主库 |
| lib/pkgconfig/OpenCL.pc, ocl-icd.pc | pkg-config 元数据 |
| bin/cllayerinfo | 已加载 layer 查询工具 |
| include/ocl_icd.h | 生成的 ICD 绑定头 |
| licenses/COPYING | 许可证文本 |

## 注意事项

1. 本包与 opencl-icd-loader 提供相同的 libOpenCL 运行时接口，两者不可同时链接，下游二选一。
2. make check 依赖本地 vendors/*.icd fixture（构建树内自动生成），无需系统 /etc/OpenCL/vendors 写权限。
3. workaround 套件中 1 个用例预期返回码为 3（无 workaround 的 buggy ICD 路径），属上游设计的负向断言，计入 34 用例总数而非失败。

## 2026-09-06 preflight failure and fix (unverified, pending re-run)

- Failure: main build plus make check 34/34 passed, but test_package cmake configure failed with CMakeDeps Library OpenCL not found in package (OpenCL-Target-release.cmake, conan_package_library_targets).
- Root cause: package_info declared cpp_info.libs OpenCL with default libdirs lib only; aarch64 autotools triplets may install to lib64, and the unversioned libOpenCL.so dev link is only a libtool symlink. Either case makes find_library fail. Dummy ICD leftovers under lib/ocl-icd were also observed in the install log.
- Fix in conanfile.py package(): remove lib/ocl-icd and lib64/ocl-icd leftovers if install-exec-hook did not run, drop .la in both libdirs, restore the unversioned libOpenCL.so link from the versioned file when missing, and fail fast with a clear message when no libOpenCL artifact exists.
- Fix in package_info(): libdirs lib plus lib64, system_libs dl and pthread on Linux/OHOS for static consumers.
- Upstream tests unchanged: make check, 34 autotest cases, passed 34/34 in the failing run.

## 2026-09-06 preflight re-run (round 3, same fingerprint, unverified)

- Previous fix (libdirs lib+lib64, dev-link restore, dummy cleanup) did NOT resolve it: build hash changed so the new recipe ran, package() passed its existence check, yet CMakeDeps still reported Library OpenCL not found. The lib64-dir hypothesis is therefore rejected.
- Revised diagnosis: a file that passes a naive islink() check can still fail CMake find_library, i.e. the unversioned libOpenCL.so development link is dangling (target copy lost while the link survived), or the recorded libdirs do not match the real layout. Blind guessing ends here.
- New strategy in conanfile.py package(): always log the real lib layout (names, symlink targets, OK/DANGLING state, sizes) via _log_package_libs; repair a missing or dangling libOpenCL.so from the real versioned libOpenCL.so.*.* file (symlink first, shutil.copyfile fallback for link-less filesystems) via _repair_opencl_links; strict fail-fast via _has_opencl_lib using os.path.exists (follows symlinks, dangling links do not count) with the listing referenced in the error.
- Helpers verified by local simulation against the actual recipe AST: versioned-only layout yields a usable libOpenCL.so via the copy fallback, empty layout yields has=False with an explicit listing.
- package_info() unchanged from round 2 (libdirs lib+lib64, system_libs dl/pthread on Linux/OHOS).
- Upstream tests and test_package assertions unchanged; no test口径 change.

## 2026-09-07 preflight round 4 (unverified, pending re-run)

- Failure: `make` + `make check` 34/34 passed, but `package()` raised
  `libOpenCL not found in lib/ nor lib64/`; listing showed only two
  DANGLING links (`libOpenCL.so -> libOpenCL.so.1.0.0`,
  `libOpenCL.so.1 -> libOpenCL.so.1.0.0`) and zero real files.
  Source download also logged two github.com ConnectTimeouts before
  succeeding on retry.
- Why previous fix failed: rounds 2-3 only repaired links from files
  already inside the package folder (`libOpenCL.so.*.*` glob). When the
  versioned entity itself was never installed, there was nothing to copy
  from, so the strict `os.path.exists` check (correctly) kept failing.
  The lib64-dir hypothesis is rejected: neither lib/ nor lib64/ held a
  real file.
- New root cause: libtool `install` copies `.libs/libOpenCL.so.1.0.0`
  via the install program, which fails under HMBS limits
  (`install_shim` single-file only, `HMBS_CAP_CHMOD=0`,
  `HMBS_CAP_HARDLINK=0`), while the `ln -s` steps still succeed
  (`symlink=1`). Result: links without a target. Precedent: avahi-ui
  0.8 works around the same shim with a cp/mkdir INSTALL shim.
- New strategy (different route, no test change): keep intra-package
  `_repair_opencl_links()` (broadened to `libOpenCL.so.*` + non-empty
  check), and add `_heal_opencl_from_build()` fallback: when the package
  still lacks a real lib, search build/source roots for a real
  `libOpenCL.so.*.*` / `libOpenCL.a` built by `make` and copy it into the
  package with plain Python I/O, then rebuild the SONAME/dev links
  (symlink first, copy fallback). Absolute absence still fails fast with
  the layout listing.
- Download reliability (per task rule for source timeouts): conandata
  `url` is now an ordered list reusing the CI mirror mapping
  (`ci/conan/build_and_test.sh` GitHub rule): gh-proxy first, official
  URL last as fallback; `sha256` unchanged.
- package_info() unchanged (libdirs lib+lib64, system_libs dl/pthread).
- Upstream tests unchanged: `make check`, 34 autotest cases.

## 2026-09-07 preflight round 5 (unverified, pending re-run)

- Round-4 result: same fail-fast, now at package() line 336, with a new
  log line `WARN: ocl-icd: no real libOpenCL entity found in build
  tree; package healing skipped`. So the round-4 fallback never had a
  copy source: the live build-tree search returned zero candidates.
- Why the previous fix failed: round-4 searched the live tree at
  package() time with glob patterns and rejected every symlink
  outright. Either the .libs versioned file is itself a symlink on this
  platform, or the tree layout at package() time differs from build()
  time. Blind package-time search ends here.
- New route (different implementation): capture at build() time.
  build() now calls _stage_built_libs() right after make check 34/34,
  walking build/source roots with os.walk, logging every *OpenCL* entry
  (link target, resolvability, size) plus the searched roots and their
  top-level listings, and copying the best resolvable bytes to
  <build_folder>/_ocl_staged. package() healing order is now:
  (1) intra-package repair, (2) staged snapshot restore (primary),
  (3) live build-tree walk with symlink resolution (fallback).
  _pick_lib_source() accepts symlinks that resolve to real bytes and
  prefers versioned .so from .libs/. Absolute absence still fails fast;
  no test is skipped or stubbed.
- Local incident: while scripting the round-5 patch, a local io.open()
  with an illegal newline argument truncated conanfile.py to 0 bytes
  (open-for-write truncates before validating the argument). The file
  was reconstructed in full from the round-4 content plus the round-5
  changes; AST parse verified OK (29145 chars) with no stray escapes.
  No commit/push was performed; the worktree remains the source of
  truth for the next preflight sync.
- Upstream tests and test_package unchanged: make check 34/34 in the
  failing run; conandata mirror list retained (no download warnings in
  the round-4 log).
