- **三方库名称**：qlog（QLog 业余无线电日志软件）
- **上游版本**：v0.51.1
- **上游仓库地址**：https://github.com/foldynl/QLog
- **适配路径**：路径 A（基础适配）
- **使用知识库**：openharmony-compile-agent 技能；参考库内先例 qpdfview/0.5.0、chinese/1.0.3.r58（qmake 多前缀 QMAKEMODULES 集成）

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 163（审查方口径 162） | 来源：上游 `tests/tests.pro` SUBDIRS 共 18 个 QtTest 套件（CallsignTest、AdiFormatTest、AdiImportBenchmark、AdifRecoveryTest、AdxFormatTest、CredentialStoreTest、DataTest、FileCompressorTest、GridsquareTest、BandPlanTest、BandmapGuideTest、AlertEvaluatorTest、DxServerStringTest、HostsPortStringTest、MigrationTest、PasswordCipherTest、QuadKeyCacheTest、RigctldManagerTest），测试函数数以各二进制 `-functions` 实测为准 |
| 集成测试 | 0 | 上游无 |
| 其他测试 | 0 | — |
| **合计** | **163** | 上游含数据驱动参数化用例，实际执行时展开为 2501 项 |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试（上游，本机原生执行） | 2501 passed / 0 failed / 5 skipped | 全量真实执行 | 18/18 套件在鸿蒙 PC 本机（aarch64 原生、Qt 6.11.1 conan 环境）构建并运行，每个测试二进制退出码 0；证据见 `archives/q/qlog/0.51.1/reports/upstream-test/`（full-run.log + 18 份 QtTest 结果文件） |
| 集成测试 | 0 | 不变 | — |
| 鸿蒙特有测试 | 5 | 新增 | test_package 冒烟：①`--version` 输出 `qlog 0.51.1`；②`--help` 完整选项表；③`.codesign` ELF 签章校验；④DT_NEEDED 依赖完整性检查；⑤RUNPATH 多前缀依赖覆盖检查 |
| **合计** | **2506 项执行 / 5 skip / 0 fail** | **+2506（执行）** | |

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [ ] **否**，未修改上游任何测试用例
- [x] **是**，存在对上游测试用例的修改（请在下方逐条说明）

> 修复仅存在于**测试执行环境**（conan build 临时源码树），用于让上游测试能在本平台真实运行；
> 不修改 conandata.yml 声明的 13 个交付补丁，不影响交付制品。逐条说明：
>
> 1. `tests/BandmapGuideTest/tst_bandmapguide.cpp`：`QTEST_APPLESS_MAIN` → `QTEST_MAIN`。
>    上游缺陷：该用例使用 QSqlDatabase 但 QTEST_APPLESS_MAIN 不创建应用实例，
>    任何平台都会因缺 QCoreApplication 而失败（无 QCoreApplication 时 QSqlDatabase 直接段错误）。
>    上游 CI 未将 tests/ 纳入构建，故未暴露。修复后 13/13 通过。
> 2. `tests/AdiImportBenchmark/tst_adiimportbenchmark.cpp`：同上修复。修复后开启上游基准开关
>    QLOG_RUN_ADI_IMPORT_BENCHMARK=1 真实执行 50k ADI 导入基准，3/3 通过（58.9s）。
> 3. `tests/RigctldManagerTest/tst_rigctldmanager.cpp`：补 `#include <QTcpSocket>`——
>    源文件使用 QTcpSocket 但仅包含 QTcpServer，依赖上游桌面 Qt 的传递包含，
>    在 Qt 6.11.1 下编译失败（incomplete type）。纯头文件补全，无行为改动。修复后 19/19 通过。
>
> 除上述 3 处外，上游测试源零修改；其余 15 个套件源码原样编译原样运行。

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [x] **否**，上游已有测试用例覆盖（18 个 QTest 套件已全量真实执行，见上表）
- [ ] **是**，上游无测试用例，适配后补全了测试（请在下方说明）

## 验证结果

- 编译状态：**通过**（W3 本地 CI 模拟全门 PASS：L0 质量闸 / L1 conan create+test_package / L5 包内容；L2/L4 非阻塞告警）
- 上游测试用例通过率：**2501/2506（99.8%），0 failed**——18/18 套件在鸿蒙 PC 本机（aarch64 原生、Qt 6.11.1 conan 环境）真实构建并全部执行，每个测试二进制退出码 0；5 项 skip 均为 CredentialStoreTest 的 qtkeychain 后端不可用（鸿蒙 PC 无 D-Bus Secret Service / KWallet，套件自身 QSKIP 跳过，上游设计行为，与 manifest.yaml 功能降级申报一致），非断言失败。逐套件：CallsignTest 150、AdiFormatTest 22、AdiImportBenchmark 3（含已开启的 50k 导入基准 58.9s）、AdifRecoveryTest 17、AdxFormatTest 12、CredentialStoreTest 9 passed/5 skipped、DataTest 8、FileCompressorTest 16、GridsquareTest 105、BandPlanTest 57、BandmapGuideTest 13、AlertEvaluatorTest 1938、DxServerStringTest 47、HostsPortStringTest 18、MigrationTest 41、PasswordCipherTest 20、QuadKeyCacheTest 6、RigctldManagerTest 19。证据：`archives/q/qlog/0.51.1/reports/upstream-test/`（full-run.log + 18 份 QtTest 结果文件）
- 新增测试用例通过率：**5/5（100%）**——test_package 真实执行 aarch64 二进制，`--version`/`--help`/签章/DT_NEEDED/RUNPATH 全部通过

## 补充说明

**功能降级申报**（非缺陷，平台能力差异）：

| 功能 | 状态 |
|------|------|
| 在线地图（OSM/Esri 瓦片、卫星图层、MUF/Aurora/IBP 覆盖层） | 降级为上游自带的离线 QGraphicsView 地图（新增 `MapPageControllerOffline`），在线覆盖层为 no-op（debug 日志提示） |
| QSL 标签打印 / PDF 导出 | 不可用（qtbase-sql-dbus 构建 FEATURE_printsupport=OFF）；屏幕预览与卡片图片导出保留 |
| About 页 TLS 版本信息 | 显示 "not available"（qtbase 构建 FEATURE_ssl=OFF，源码以 `#ifndef QT_NO_SSL` 守卫） |

**构建要点**：qmake 多前缀集成（QMAKEMODULES 改写 mkspecs/modules/*.pri、qtcharts/qtserialport/qtwebsockets 模块 INCLUDEPATH 与链接库路径修正、全依赖 lib 目录注入 RPATH）；`HAMLIBVERSION_*=4/7/2` 命令行传入绕过 pkg-config；`make -j1`（R9）；ELF `.codesign` 签章位于 package() 最后一步。

**CI 修复（MR #14448，Build #79959/#81268 EOVERFLOW）**：CI worker 在 `make install` 阶段报 `Error copying …: Value too large for data type`（EOVERFLOW）。#79959 失败在 qlog 二进制拷贝；改用 python 预拷贝+Makefile no-op 后，#81268 连几十字节的 `qlog.desktop` 也报同样错误——确认根因是 qmake `qinstall`（QFile::copy）在部分 worker 的 hmdfs 上对任意文件拷贝失败，与文件大小无关（编译/链接均正常，产物仅约 118MB；本机实测 hmdfs 上 4.4GB 文件读/写循环拷贝正常）。最终修复：package() 完全弃用 `make install`，按上游 QLog.pro INSTALLS 清单用 python `shutil.copy2` 直接安装并逐文件校验大小（包内 hnp 布局仅保留 `bin/qlog`，与此前通过审查的包一致）；修复后鸿蒙 PC 本机全量 CI 重跑通过（L0/L1/L5 pass，L2/L4 非阻塞，100% pass rate）。

**产物**：13 个补丁（含离线地图 fallback、打印服务禁用、TLS 守卫、.ui QWebEngineView→MapWidget 替换等），conandata.yml 仅官方 URL + sha256（PF7）；已知限制与问题表详见 `archives/q/qlog/0.51.1/notes.md`；上游测试全量执行证据见 `archives/q/qlog/0.51.1/reports/upstream-test/README.md`（逐套件结果表、skip 原因、3 处测试专用修复申报）。
