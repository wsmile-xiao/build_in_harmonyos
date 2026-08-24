# attica 6.28.0 适配笔记（OHOS / HarmonyOS PC aarch64）

## 一、软件与版本差异（相对 6.18.0）

- 版本：6.28.0（KDE Frameworks 6 Open Collaboration Services 客户端库）
- 顶层 CMakeLists 门槛变化：
  - `cmake_minimum_required(VERSION 3.29)`（6.18.0 为 3.16；设备 cmake 4.1.2 满足）
  - `REQUIRED_QT_VERSION` 6.7.0 → **6.9.0**（Qt6 Core+Network；qtbase/6.11.1 满足）
  - `find_package(ECM 6.18.0)` → **`find_package(ECM 6.28.0 NO_MODULE REQUIRED)`**，故必须先新增 ecm/6.28.0（本地缓存构建，不经 conan upload）
  - `ecm_set_disabled_deprecation_versions(QT 6.10)` → `QT 6.11`
- 源码变化（6.28.0）：新增 `platformdependent_v3.cpp` 等（非编译/链接路径风险，scout 已确认不影响 OHOS 构建）

## 二、OHOS 适配要点（逻辑与 6.18.0 保持一致）

1. **依赖**：`qtbase/6.11.1`（cmake_find_mode=none，靠自带 Qt6Config.cmake）+ `ecm/6.28.0`（build-scripts tool_requires）。
2. **qtbase 桥接**：qtbase 不开 CMakeDeps 生成 Qt6 target，`generate()` 手动写 `conan_cmakedeps_paths.cmake`，
   将 qtbase `lib/cmake` PREPEND 进 CMAKE_PREFIX_PATH（lib 与 include 同步），并设
   `CMAKE_FIND_PACKAGE_PREFER_CONFIG ON`。ki18n 经验：凡 find 模块要读的路径都要显式写进该文件。
3. **ECM_MODULE_PATH**：CMakeDeps 的 ECMConfig.cmake 不向项目传播该变量；`generate()` 里
   `tc.variables["ECM_MODULE_PATH"]` 手动指向 ecm 包 `share/ECM/{modules,find-modules,kde-modules}`。
4. **KF 平台检查**：attica 6.28.0 未 include `KDEMetaInfoPlatformCheck`，不会触发 FATAL_ERROR；
   `KF_IGNORE_PLATFORM_CHECK=TRUE` 保留为防御性 no-op。
5. **测试**：BUILD_TESTING=ON；上游 CTest 注册 configtest/persontest/providertest 三个；
   `ctest -E "^providertest$" --no-tests=error` 排除外网 OCS 测试（autoconfig.kde.org / invalid-url.org，会挂起）。
   - projecttest 是 `ecm_mark_as_test` 标记的手工 Qt Widgets GUI，非 CTest 条目（构建不运行）。
   - privatedatatest.cpp 是未注册的死文件（CMake 不引用）。
   - reuse 工具缺失 → ECMCheckOutboundLicense 的 licensecheck 系列不注册。
6. **运行时/测试环境**：`_prepare_ctest_runtime_links()` 符号链接 + copy2 兜底（HMDFS 软链限制）；
   HOME/XDG_* 隔离；`QT_QPA_PLATFORM=offscreen`；`CTEST_PARALLEL_LEVEL=1`；`CTEST_OUTPUT_ON_FAILURE=1`。
7. **TMPDIR**：必须 `export TMPDIR=$HOME/tmp`（设备 /tmp 只读）。

## 三、构建记录

- ecm/6.28.0：源 extra-cmake-modules-6.28.0.tar.xz，SHA-256=`a32e24b267e8528d0253bc8df18bdc00e676560a43b796533e1b1406f4eef4db`
  （设备 sha256sum 与官方 .sha256 双一致）。recipe 放设备独立临时目录
  `（设备本地临时目录，不进交付分支）`（不进 attica worktree）。
- attica/6.28.0：源 URL/SHA 见 conandata.yml（scout 已双重复核）。
- CI 命令：`conan create archives/a/attica/6.28.0 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=... --build=missing`
  （ohpcd remote 不可匿名访问 → L0i registry 检查不可用，本轮直接用 conan create 验证）。

## 四、验证结果（CI 后回填）

- [x] upstream CTest 2/2（configtest/persontest）
- [x] test_package 1/1（Attica value-object 消费者 smoke）
- [x] L0/L1/L4/L5 门禁（L0i registry 门禁因 ohpcd 不可匿名访问未单独运行，详见 manifest）

## 五、ECM 版本降级补丁（CI L0i 修复）

- 问题：attica 6.28.0 顶层 CMakeLists 要求 `find_package(ECM 6.28.0 NO_MODULE)`，但 ohpcd 制品仓只有 ecm/6.20.0/6.26.0/7.0.7（7.0.7 为 autotools 同名冲突包，非 KDE ECM），ecm/6.28.0 未发布且老师禁止发布新制品到制品仓，CI L0i 门禁（R36 依赖先发布）因此失败。
- 方案：降级使用已发布的 ecm/6.26.0，补丁 `patches/0001-lower-ecm-version.patch` 将 `find_package(ECM 6.28.0 NO_MODULE)` 改为 `find_package(ECM 6.26.0 NO_MODULE)`。
- 兼容性验证：attica 6.28.0 用到的全部 13 个 ECM 模块（KDEInstallDirs/KDECMakeSettings/KDEFrameworkCompilerSettings/KDEGitCommitHooks/ECMGenerateExportHeader/ECMGeneratePkgConfigFile/ECMCheckOutboundLicense/ECMSetupVersion/ECMGenerateHeaders/ECMQtDeclareLoggingCategory/ECMDeprecationSettings/ECMGenerateQDoc/ECMFeatureSummary）在 ecm/6.26.0 中均存在；`ecm_set_disabled_deprecation_versions(QT 6.11)` 的 ECMDeprecationSettings 在 6.26.0 与 6.28.0 差异仅为 KF 警告宏分支（QT_DISABLE_DEPRECATED_BEFORE 逻辑一致），无版本上限校验，兼容。
- 影响：recipe 依赖从 ecm/6.28.0 改为 ecm/6.26.0（tool_requires），CI L0i 可解析已发布依赖。

## 六、验证结果（CI round-4，2026-08-22）

- [x] upstream CTest 2/2（configtest/persontest），providertest 因需外网 OCS 排除（N/A（未运行））
- [x] test_package 1/1（Attica value-object 消费者 smoke，7 断言，PASS: Attica value objects OK）
- [x] 补丁 0001-lower-ecm-version.patch 应用成功（conan create 日志 "Apply patch (file): patches/0001-lower-ecm-version.patch"），干净构建 EXIT=0
- [x] L0/L1/L4/L5 门禁（L0i registry 门禁因 ohpcd 不可匿名访问未单独运行；CI 官方侧 L0i 以已发布依赖 ecm/6.26.0 可解析）
- 完整日志：/storage/Users/currentUser/.local/state/oh-device-porting/runs/attica-6.28.0/logs/attica-6.28.0-ci-round4.log
