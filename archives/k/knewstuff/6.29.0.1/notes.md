# knewstuff 6.29.0 notes（R03）

## R03 追加（产物绝对依赖路径清除 + finish/W3 返工）

- **绝对路径门禁达成**：全产物 `readelf -d` 扫描 **NO absolute/relative NEEDED entries**
  （`reports/absolute-path-r03-after.md`）。R02 遗留的静态库/INTERFACE 传递绝对项（core 的
  ki18n/kcoreaddons、widgets 的 attica/kcoreaddons、dialog 的 kconfig/ki18n/attica/kcoreaddons）
  全部清除为可重定位基名。
- **R05 补丁 0004 扩展为 4 文件**（core/widgets/qtquick/dialog）：
  - 全 KF6 依赖改 `-l` 裸名 + PRIVATE `target_link_directories`；静态库
    `knscore_jobs_static` / `knewstuff_qml_STATIC` 的 KF6 依赖改 PRIVATE `-l`；
  - KF6NewStuffCore INTERFACE 不再导出 Attica/CoreAddons（导出契约干净，消费方无需 -L）；
  - 插件/工具直接使用的 KF6 符号由各目标显式 `-l` 提供；
  - 树内目标 KF6::NewStuffCore 保留 PUBLIC 以向插件传播 include。
- **conanfile.py generate()**：注入 `KNEWSTUFF_DEP_LIB_DIRS`、全局
  `CMAKE_CXX/C_STANDARD_INCLUDE_DIRECTORIES`（含 `include/KF6/<Module>`）、
  `CMAKE_EXE/SHARED/MODULE_LINKER_FLAGS=-L<dep libs>`。
- **conan create**（禁 `--build=missing`）：RC=0，上游 CTest 4/4、test_package 1/1、
  OH 二进制 `knewstuff-dialog6 --help` 执行成功。
- **finish/W3 后台 worker**：按任务要求以 team 后台 worker 提交并轮询至自然终态——该环境
  team worker 角色仅只读工具（无 bash/exec），无法执行 `ohc-run.py finish`。R02 finish 证据：
  Step1-4 通过（conan-verify 全 PASS）、Step5 W3 的 conan create 段曾被 300s 通道上限截断。
  恢复条件：分析端提供具备 bash/exec 能力的后台 worker 通道重跑 finish/W3。

## R02 / R01 基础（沿用）

见上文 R02 / R01 段落：kpackage/6.18.0.1 消费、test_package 修复、R05 起点、ECM/KF 版本降低等。

## Scope

KDE Frameworks 6 KNewStuff（下载应用资产/Get Hot New Stuff），产出 KF6NewStuffCore、
KF6NewStuffWidgets、newstuffqmlplugin 与 knewstuff-dialog6。本归档按 R02 消费验证返工
更新：依赖 kpackage/6.18.0.1（已合入修复版），上游测试/test_package/OH 二进制测试全部通过。

## Adaptations（R01 基础）

- `KF_IGNORE_PLATFORM_CHECK=TRUE`：绕过 KDE 平台白名单（OHOS 不在列表内）。
- `KF_SKIP_PO_PROCESSING=ON`：跳过翻译目录生成。
- `BUILD_TESTING=ON` + ctest 上游测试；`QT_QPA_PLATFORM=offscreen` 无头运行。
- 可选依赖 KF6Kirigami / KF6Syndication 置为未找到（ohpcd 未发布，不进基线包）。
- `ECM_MODULE_PATH`、`conan_cmakedeps_paths.cmake` 手工写入：qtbase/qtdeclarative 与
  KF6 包均为 `cmake_find_mode=none`，CMakeDeps 不自动把其 lib/cmake 目录加入搜索路径。
- 补丁 0001：ECM 6.29.0→6.26.0、KF_DEP_VERSION 6.29.0→6.18.0（ohpcd 依赖版本上限）。
- 补丁 0002/0003：KF6I18nQml 可选化 + QML 上下文替换。

## Adaptations（R02 新增）

- **依赖**：`kpackage/6.18.0` → `kpackage/6.18.0.1`（消费已合入修复版；`libKF6Package.so`
  DT_NEEDED 已无 `.cache/conan2` 绝对路径，readelf 验证通过）。
- **补丁 0004（R05 可重定位链接）**：
  - KF6NewStuffCore / KF6NewStuffWidgets 设置显式 SONAME（`-Wl,-soname`），消除打包二进制
    对自有库的 build-tree 相对路径 NEEDED（`../../../bin/...`）。
  - KF6 依赖以 `-l` 裸名 + PRIVATE `target_link_directories(${KNEWSTUFF_DEP_LIB_DIRS})` 链接，
    使 lt 记录 `libKF6Attica.so` 等基名而非本机 `.conan2` 绝对路径；public/attica/coreaddons
    走 INTERFACE 目标名传导给消费者；include 目录 PRIVATE 补回。
  - conanfile.py `generate()` 新增 `KNEWSTUFF_DEP_LIB_DIRS` 变量（各 KF6 依赖 lib 目录）。
- **test_package**：
  - `generate()` 把所有依赖包目录（含传递 KF6 依赖）PREPEND 进 CMAKE_PREFIX_PATH——
    KF6NewStuffCoreConfig 内 `find_dependency(KF6Attica)` 首次真实执行时暴露的查找失败。
  - test.cpp include 修正为规范路径 `<KNSCore/Entry>`/`<KNSCore/Author>`（安装头位于
    `include/KF6/KNewStuffCore/KNSCore/`，转发头标注 `#include <KNSCore/Entry>`）。
  - test() 新增 OH 平台二进制测试：以 conan 运行环境 + `QT_QPA_PLATFORM=offscreen`
    执行打包 `knewstuff-dialog6 --help`（真实平台二进制在 OH 运行时加载执行）。

## Verification（R02 实测）

- `conan create`（REDUCE_PRIVILEGES off、无 `--build=missing`）：RC=0
- 上游 CTest **4/4**：knewstuffentrytest / knewstuffauthortest / knewstuffenginetest /
  installationtest（R01 全部因 kpackage 绝对 NEEDED 不可运行 → R02 全部通过）
- test_package：ctest 1/1 + 直接运行 `PASS: KNewStuffCore Entry API smoke test`
  + `knewstuff-dialog6 --help` 输出 Usage（RC=0）
- 产物 DT_NEEDED：库直接依赖全部为可重定位基名；`knewstuff-dialog6` 对自有库
  `libKF6NewStuffCore.so`（唯一残差为本机 `.conan2` 绝对路径的传递/静态链接项，
  已留档为后续可重定位收尾项）
- conan-verify（ohc-run）：G1/G2/G3/G4/L2/L4/L5 全 PASS
- W2/W3/原子性：见 reports/atomicity-audit.md；W3 包装器 conan create 段受执行通道 300s
  上限截断（外部项，非库缺陷；独立 conan create 已证明 RC=0）

## 已知外部项 / 恢复条件

- ohpcd 远端匿名 conan 读取被 cnb.cool 策略拒绝（`system acceleration policy not enabled`，
  证据见 reports/registry-diagnostic-r02.md）。恢复条件：分析端恢复 ohpcd 匿名读取或在
  新环境重新 seed cache。kpackage/6.18.0.1 发布 binary 已在本地 cache，消费验证不受影响。
- W3/finish 的 CI 包装器需在带后台 worker 的通道重跑以完整闭环（当前通道 300s 上限）。
---

**编译结束**: 2026-09-05 02:04
**最终状态**: built
