# attica 6.14.0 适配笔记（OHOS / HarmonyOS PC aarch64）

## 一、任务背景与底稿

- **平台任务指定版本**（contrib-3595，积分赛-依赖）：制品仓已有 attica 6.18.0/6.28.0，
  本任务为 6.14.0 首次适配（R37：首次适配用上游版本号原样）。6.14.0 早于已有归档版本，
  属于平台任务卡给定的版本要求。
- **底稿**：`archives/a/attica/6.18.0`（zxyAtom，结构同源）。6.28.0 归档仅作对比参考。

## 二、与 6.18.0 / 6.28.0 的差异

| 项 | 6.14.0（本任务） | 6.18.0（底稿） | 6.28.0 |
|---|---|---|---|
| ECM 要求 | `find_package(ECM 6.14.0 NO_MODULE)` | `find_package(ECM 6.18.0 NO_MODULE)` | `find_package(ECM 6.28.0 NO_MODULE REQUIRED)` |
| ECM 依赖选择 | ecm/6.26.0 已满足（≥6.14.0），**无需补丁** | ecm/6.26.0 满足（≥6.18.0），无补丁 | ecm/6.26.0 不满足（<6.28.0），需 `0001-lower-ecm-version.patch` 降级 |
| Qt 最低版本 | 6.7.0（qtbase/6.11.1 满足） | 6.7.0 | 6.9.0 |
| cmake_minimum | 3.16 | 3.16 | 3.29 |
| 上游 autotests | configtest/persontest/providertest（CTest 注册） | 同左 | 同左 |
| 平台检查 | 无 include（KF_IGNORE_PLATFORM_CHECK 为防御性 no-op） | 同左 | 同左 |

## 三、OHOS 适配要点（逻辑与 6.18.0 底稿保持一致）

1. **依赖**：`qtbase/6.11.1`（cmake_find_mode=none，靠自带 Qt6Config.cmake）+
   `ecm/6.26.0`（tool_requires）。W0 已用 `conan download --only-recipe` 实测两者在
   ohpcd 制品仓存在（R35/R36）。
2. **qtbase 桥接**：qtbase 不开 CMakeDeps 生成 Qt6 target，`generate()` 手动写
   `conan_cmakedeps_paths.cmake`，将 qtbase `lib/cmake` PREPEND 进 CMAKE_PREFIX_PATH
   （lib 与 include 同步），并设 `CMAKE_FIND_PACKAGE_PREFER_CONFIG ON`。
3. **ECM_MODULE_PATH**：CMakeDeps 的 ECMConfig.cmake 不向项目传播该变量；
   `generate()` 里 `tc.variables["ECM_MODULE_PATH"]` 手动指向 ecm 包
   `share/ECM/{modules,find-modules,kde-modules}`。
4. **KF 平台检查**：`KF_IGNORE_PLATFORM_CHECK=TRUE`（6.14.0 metainfo platforms 不含
   OHOS；源码未 include KDEMetaInfoPlatformCheck，该项为防御性保留）。
5. **测试**：`BUILD_TESTING=ON`；上游 CTest 注册 configtest/persontest/providertest
   三个；`ctest -E "^providertest$" --no-tests=error` 排除外网 OCS 测试
   （autoconfig.kde.org / invalid-url.org，OHOS runner 上会挂起）。
   - projecttest 是 `ecm_mark_as_test` 标记的手工 Qt Widgets GUI，非 CTest 条目。
   - privatedatatest.cpp 是未注册的死文件（CMake 不引用）。
   - reuse 工具缺失 → ECMCheckOutboundLicense 的 licensecheck 系列不注册。
6. **运行时/测试环境**：`_prepare_ctest_runtime_links()` 符号链接 + copy2 兜底
   （HMDFS 软链限制）；HOME/XDG_* 隔离；`QT_QPA_PLATFORM=offscreen`；
   `CTEST_PARALLEL_LEVEL=1`；`CTEST_OUTPUT_ON_FAILURE=1`。
7. **TMPDIR**：设备 /tmp 只读，构建时 `export TMPDIR=$HOME/tmp`。

## 四、验证记录（W3 本地 conan create）

- 命令：`conan create archives/a/attica/6.14.0 --user=ohpcd --channel=stable
  -pr:h=$HOME/.conan2/profiles/ohos-aarch64 -pr:b=$HOME/.conan2/profiles/ohos-aarch64
  --build=missing`（设备负载高，timeout 3600s；PYTHONPATH 需保留环境原有
  `pip-global` 前缀再追加 pyshim，覆盖会导致 conan 报 ModuleNotFoundError: distro）。
- 上游源码 SHA256 双重复核：本地 sha256sum 与官方 `.sha256` 文件一致
  （`7c3556afeb0ae0e932c2e4d309df4905f3e2f41af3e3b38051b49d9f279357c1`）。
- 上游 CTest：**2/2 通过**（configtest 0.10s、persontest 0.08s），providertest 排除（外网依赖）。
- test_package：**1/1 通过**（`PASS: Attica value objects OK`）。
- 产物：`attica/6.14.0@ohpcd/stable#6c58c4911d9398ad4fadab2fc2593661:57ffd8c720a5bfee7e8827990cd6550a49181c1b`。

## 四点五、与底稿 6.18.0 的实现差异（本版新增适配）

- **configure 阶段运行时环境注入**（6.18.0 底稿没有）：KDEInstallDirs6 → ECMQueryQt
  在 configure 时执行 qtbase 的 `qtpaths`，该二进制链接 OHOS libc++/libunwind；
  qtbase 的 conan 包不带这些 so，需在 LD_LIBRARY_PATH 前置 OHOS SDK llvm lib 目录
  （`/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib/aarch64-linux-ohos`，
  含 `*` 通配 fallback）。6.18.0 当年在远程 runner（环境自带 LD_LIBRARY_PATH）上构建，
  未暴露此问题；本机与 CI 环境直接构建会报 `Qt6 qtpaths call failed: 127` +
  `Error loading shared library libc++_shared.so`。修复为 conanfile 内建
  `_ohos_sdk_lib_dirs()`（R33：路径来自配方逻辑而非裸 shell env，可移植）。
- **DT_SONAME 注入**（attica5/5.116.0 平台验证过的模式）：HarmonyOS 不是 CMake 的
  versioned-SONAME 平台，`CMAKE_SHARED_LIBRARY_SONAME_<lang>_FLAG` 未定义导致
  `libKF6Attica.so` 无 DT_SONAME（CI L5 soname gate fail）。注入
  `CMAKE_PLATFORM_NO_VERSIONED_SONAME=TRUE` + `CMAKE_SHARED_LIBRARY_SONAME_C/CXX_FLAG="-Wl,-soname,"`，
  保留 SONAME 发射但跳过版本化符号链接（部分 OHOS/HMDFS 构建路径不接受）。

## 五、上游测试未执行项及豁免说明

- `providertest`：依赖活跃外网 OCS 端点
  （`https://autoconfig.kde.org/ocs/providers.xml`、`https://invalid-url.org/ocs/providers.xml`），
  在 OHOS runner 上会挂起等待外网响应，排除执行（与 6.18.0/6.28.0 先例一致）。
- `tests/projecttest`：上游标记 `ecm_mark_as_test()` 的手工 Qt Widgets 可执行程序，
  未注册为 CTest 条目，构建但不作为测试运行。
- ECM outbound SPDX license test：runner 无 `reuse` 工具（ReuseTool not found），不注册。
- API 文档生成（QCH）：上游 CMake 找不到 Qt6Tools/Qt6ToolsTools，未执行
  （BUILD_QCH 默认 OFF）。
---

**编译结束**: 2026-09-03 01:31
**最终状态**: built
