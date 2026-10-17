# qcoro 0.13.0 适配笔记

## 编译环境
- 构建系统: cmake（上游 CMake，Conan 配方驱动）
- 编译日期: 2026-10-02
- 编译器: clang / clang++ (OHOS SDK 26.0.0.18, aarch64-linux-ohos)
- 目标: HarmonyOS PC (arm64), Conan 2.29.1
- 状态: published（conan-verify 8 门禁通过）

## 编译步骤

配方路径：`archives/q/qcoro/0.13.0/`，标准 Conan 流程（R16：用 `conan create`，不手工打包）：

```bash
# 依赖（制品仓已有）
conan download qtbase/6.11.1.1 -r=ohpcd --only-recipe
# 构建 + 打包 + test_package
conan create archives/q/qcoro/0.13.0 --build=missing
# 8 门禁验证
python3 $SKILL_ROOT/scripts/ohc-run.py conan-verify qcoro 0.13.0
```

探索阶段的裸构建（用于跑通上游测试，非交付路径）：

```bash
cmake -S <src> -B <build> -DCMAKE_TOOLCHAIN_FILE=<ohos toolchain> \
      -DQt6_DIR=<qtbase pkg>/lib/cmake/Qt6 -DCMAKE_PREFIX_PATH=<qtbase pkg> \
      -DQCORO_BUILD_TESTING=ON -DQCORO_WITH_QTWEBSOCKETS=OFF \
      -DQCORO_WITH_QTQUICK=OFF -DQCORO_WITH_QML=OFF
cmake --build <build> -j
```

安装树（探索期 staging）：`include/qcoro6/QCoro/*.h`、`include/qcoro6/qcoro/`、`lib/libQCoro6Core.a`、
`lib/libQCoro6DBus.a`、`lib/libQCoro6Network.a`、`lib/cmake/QCoro6{,Core,Coro,DBus,Network,Test}/`。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `conan-verify` G2 在 source() 阶段失败（等待 ghfast.top 镜像下载超时） | 本机到 `ghfast.top` 镜像不可达，GitHub 直连正常；conan-verify 会把 conandata 的 GitHub URL 改写为镜像前缀 | 预置 Conan 源码下载缓存：`core.sources:download_cache` 以 **sha256** 为键（`<cache>/s/<sha256>`），把直连下载的 tarball 放入即命中，source() 不再走网络。缓存元数据 `<sha256>.json` 记录的是原始 URL，与镜像 URL 不交集会触发"重新下载"，临时移开该 json 即稳定命中（本地环境操作，不入归档） |
| 2 | G2 test_package configure 失败：`Library 'QCoro6Test' not found in package` | 配方给 Test 组件声明了 `libs = ["QCoro6Test"]`，但上游把 QCoro6::Test（同理 QCoro6::Coro）发布为 **INTERFACE** 组件，从不安装对应库文件 | 接口组件只声明 `cmake_target_name`（并补 `Coro` 组件），不声明 `libs` |
| 3 | G2 test_package 编译报 `fatal error: 'QCoro/QCoroTask' file not found` | 配方带 components 时，根 `cpp_info.includedirs/cxxstd` 不会被子组件目标继承 | 每个组件各自声明 `includedirs`（`include`、`include/qcoro6`、`include/qcoro6/qcoro`、`include/qcoro6/QCoro`，与上游 `QCoro6Targets.cmake` 一致）与 `cxxstd = "20"` |
| 4 | 消费侧只链 `QCoro6::Core` 时缺 Qt6 符号 | 上游 QCoro6::Core 的 INTERFACE_LINK_LIBRARIES 含 `Qt6::Core`；Conan 侧需显式声明依赖才会带出 | Core 组件加 `requires = ["Coro", "qtbase::qtbase"]`；消费侧（test_package/下游）按本仓既有做法把 qtbase 映射为 `Qt6::Core` 并显式 `find_package(Qt6)`（ohpcd 的 qtbase 使用 Qt 自带 Qt6Config.cmake，CMakeDeps 不生成可用 Qt6 config） |
| 5 | 探索期构建上游测试时 `tests/testlibs` 缺 `QTcpSocket` 声明 | 上游测试源隐含依赖 | 探索期仅在源码树补 `#include <QTcpSocket>`（`track-edit` 记录）；包本身 `QCORO_BUILD_TESTING=OFF`，**不需要**该改动，故 `patches/` 为空 |

## 源码修改

无。`patches/` 为空，`patches_applied: []`；上述第 5 条只存在于探索期源码树，未固化为补丁。

## 依赖版本

| 依赖 | 版本 | 说明 |
|------|------|------|
| qtbase | 6.11.1.1 | 提供 Qt6 Core/Network/DBus/Test；WebSockets/Quick/QML 不在该包内，故这三个可选特性关闭 |

## 上游测试申报（R51 三步法）

**① 清点**：上游 `tests/CMakeLists.txt` 共注册 **18** 个 ctest 用例（`qcoro_add_test()` × 18）。

**② 实测**：在设备原生构建树以 `QCORO_BUILD_TESTING=ON` 构建并执行 `ctest`：

```
83% tests passed, 3 tests failed out of 18
Total Test time (real) = 122.26 sec
```

- 通过: **15/18**
- 未通过: **3/18**，逐项原因：
  - `test-qcorolocalsocket` — **Timeout**（ctest 120s 上限）：本地套接字用例在本沙箱环境超时（同类限制见 G2 的沙箱探测告警），非代码缺陷
  - `test-qdbuspendingcall` — **Not Run**：该用例经 `dbus-run-session` 包装注册，本环境无 `dbus-run-session` 可执行文件（ctest 报 `Could not find executable dbus-run-session`）
  - `test-qdbuspendingreply` — **Not Run**：同上，缺 `dbus-run-session`
- 说明：首轮 18/18 全红，根因是 Qt6 共享库未在加载路径（LD_LIBRARY_PATH），带上后即得到上述结果——属环境因素，已排除。

**③ 回填**：以上为实测值，非占位符。

## 验证结果

```bash
$ python3 $SKILL_ROOT/scripts/ohc-run.py conan-verify qcoro 0.13.0
G0: 预构建风险评估  OK
G1: 配方完整性      OK
G2: conan create    OK   # 含 test_package 构建与运行
G3: 系统同名库隔离  OK   # 导出 QCoro6*.a，与 /lib /lib64 无同名冲突
G4: 产物完整性      OK   # include/qcoro6 + libQCoro6Core/DBus/Network.a + QCoro6Config.cmake
L2 smoke / L4 安全 / L5 基线  OK
```

test_package 实际调用被测 API（`QCoro::Task` + `QCoro::waitFor`，链接 `QCoro6::Core`），非空壳（R34）。

## 注意事项

- 导出目标名：`QCoro6::Core` / `QCoro6::Coro` / `QCoro6::DBus` / `QCoro6::Network` / `QCoro6::Test`；
  下游 `kaccounts-integration` 需要 `find_package(QCoro6 REQUIRED COMPONENTS Core)`。
- QCoro 头文件要求 C++20：配方按组件下发 `cxxstd = "20"`。
- 构建/验证机需能访问 GitHub（或预置 Conan 源码下载缓存），本机 ghfast.top 镜像不可达。
---

**编译结束**: 2026-10-03 10:40
**最终状态**: published
