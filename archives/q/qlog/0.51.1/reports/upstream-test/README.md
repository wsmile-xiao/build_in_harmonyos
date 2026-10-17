# 上游测试用例真实执行报告 — qlog 0.51.1（HarmonyOS PC aarch64 本机原生）

- 执行日期：2026-10-07
- 执行环境：HarmonyOS PC aarch64 本机（HongMeng Kernel 1.12.0），Qt 6.11.1（conan ohpcd 制品，
  qtbase/6.11.1 + qtbase-gui + qtbase-sql-dbus + qtcharts + qtserialport + qtwebsockets +
  qtkeychain/0.14.2 + hamlib/4.7.2 + sqlite3/3.53.4 + openssl/3.5.6.1.2 + zlib/1.3.2.1），
  工具链 clang 15（/data/service/hnp/bin）。测试在目标平台原生构建并原生执行（非交叉产物）。
- 上游源码：https://github.com/foldynl/QLog tag v0.51.1，sha256
  997a6ca09b05bd7cbbfb087c41e92a619feee6584bfb8d7f45b863d6e1293657（与 conandata.yml 一致），
  并应用本适配 13 个补丁（与 conan create 同一源码基线）。

## 结果总览

| 套件 | 测试函数（-functions 口径） | 执行结果 |
|------|------|------|
| CallsignTest | 2 | Totals: 150 passed, 0 failed, 0 skipped |
| AdiFormatTest | 20 | 22 passed, 0 failed, 0 skipped |
| AdiImportBenchmark | 1 | 3 passed, 0 failed, 0 skipped（benchmark 已以 QLOG_RUN_ADI_IMPORT_BENCHMARK=1 开启运行，58.9s） |
| AdifRecoveryTest | 15 | 17 passed, 0 failed, 0 skipped |
| AdxFormatTest | 10 | 12 passed, 0 failed, 0 skipped |
| CredentialStoreTest | 9 | 9 passed, 0 failed, **5 skipped**（平台限制，见下） |
| DataTest | 6 | 8 passed, 0 failed, 0 skipped |
| FileCompressorTest | 14 | 16 passed, 0 failed, 0 skipped |
| GridsquareTest | 16 | 105 passed, 0 failed, 0 skipped |
| BandPlanTest | 8 | 57 passed, 0 failed, 0 skipped |
| BandmapGuideTest | 11 | 13 passed, 0 failed, 0 skipped |
| AlertEvaluatorTest | 4 | 1938 passed, 0 failed, 0 skipped |
| DxServerStringTest | 2 | 47 passed, 0 failed, 0 skipped |
| HostsPortStringTest | 5 | 18 passed, 0 failed, 0 skipped |
| MigrationTest | 1 | 41 passed, 0 failed, 0 skipped |
| PasswordCipherTest | 18 | 20 passed, 0 failed, 0 skipped |
| QuadKeyCacheTest | 4 | 6 passed, 0 failed, 0 skipped |
| RigctldManagerTest | 17 | 19 passed, 0 failed, 0 skipped |
| **合计（18 套件）** | **163（审查方口径 162，差 1 为 init/cleanup 类槽函数计数差异）** | **2501 passed, 0 failed, 5 skipped（数据驱动参数化行展开后）** |

每个测试二进制退出码均为 0（18/18 exit=0，见 full-run.log）。

## skip 明细（5 项，均有具体技术原因）

- CredentialStoreTest 5 项：`Credential store backend not available (save failed)` ——
  qtkeychain 的后端为 D-Bus Secret Service / KWallet，鸿蒙 PC 无该系统服务，
  凭据保存后端不可用（与 manifest.yaml 功能降级申报一致）。套件自身以 QSKIP 跳过，非断言失败。
- 说明：AdiImportBenchmark 的 50k 基准为上游设计的环境变量开关型用例，
  本次已显式开启并真实执行通过（reports/upstream-test/adi-import-benchmark-enabled.log）。

## 测试专用修复申报（仅测试构建使用，未进入配方/补丁集）

上游测试源存在 2 处平台无关缺陷（QTEST_APPLESS_MAIN 不创建应用实例，
而用例使用 QSqlDatabase —— 在任何平台都会因缺 QCoreApplication 失败/崩溃，
上游 CI 未纳入 tests/ 因此未暴露）：

1. `tests/BandmapGuideTest/tst_bandmapguide.cpp`：`QTEST_APPLESS_MAIN` → `QTEST_MAIN`（该 .pro 已含 gui 模块）
2. `tests/AdiImportBenchmark/tst_adiimportbenchmark.cpp`：同上（sql-only，QTEST_MAIN 创建 QCoreApplication）
3. `tests/RigctldManagerTest/tst_rigctldmanager.cpp`：补 `#include <QTcpSocket>`
   （源文件使用 QTcpSocket 但仅包含 QTcpServer，依赖上游桌面 Qt 的传递包含）

以上 3 处仅存在于本次测试执行环境（conan build 临时源码树），不修改
conandata.yml 声明的补丁集，不影响交付制品。

## 测试构建环境备注（仅测试执行，非配方行为）

- qmake 生成测试 Makefile 时 `qt_functions.prf` 的 `qtAddTargetEnv` 未将
  QMAKE_HOST.os=HarmonyOS 归入 LD_LIBRARY_PATH 分支（主程序构建路径不触发该分支），
  在 conan 缓存内 qtbase mkspecs 临时补 `|HarmonyOS` 后正常（conan 缓存文件，非仓库改动）。
- 运行期环境：`conanrun.sh`（conan 聚合 LD_LIBRARY_PATH）+ `QT_QPA_PLATFORM=offscreen`
  + `QT_PLUGIN_PATH=<qtbase包>/plugins`（QSQLITE 插件定位）。

## 证据文件

- `full-run.log` — 18 套件完整运行日志（含每套件 exit code）
- `<Suite>-result.txt` — 18 份 QtTest 文本结果（含全部 PASS/SKIP 明细）
- `adi-import-benchmark-enabled.log` — 开启上游基准开关后的真实基准运行
