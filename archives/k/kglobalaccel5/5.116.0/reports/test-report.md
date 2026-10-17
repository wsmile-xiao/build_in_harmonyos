# kglobalaccel5 5.116.0 测试报告

日期：2026-09-21
环境：OpenHarmony PC（aarch64, clang 15.0.4, libc++）——本机构建本机执行
profile：ci/conan/profiles/ohos-aarch64
构建命令：`conan create archives/k/kglobalaccel5/5.116.0 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing`

## 1. 构建验证（conan create）

- 结果：**成功**（W3 门禁 L0/L1/L4/L5 pass；conan create 与 W3 完整日志
  仅本地留存，依规不入库——CI 侧执行证据由 PR 流水线日志承载）。
- 产物：`lib/libKF5GlobalAccel.so`（SONAME 无版本号，L5 门禁通过）、
  `include/KF5/KGlobalAccel/…`、`lib/cmake/KF5GlobalAccel/{Config,Targets…}.cmake`、
  `share/dbus-1/interfaces/kf5_org.kde.KGlobalAccel.xml`。
- 裁剪：kglobalacceld 守护进程 + kglobalaccel CLI（X11/XCB-only，OHOS 无
  X11 会话；BUILD_RUNTIME=OFF），包内无守护进程为预期行为。
- 上游测试套件在本配置下**保持构建**：
  `patches/0002-build-autotest-without-runtime.patch` 将
  `autotests/kglobalshortcuttest` 的链接从守护进程侧私有目标
  `KF5::GlobalAccelPrivate` 改为公共库 `KF5::GlobalAccel` +
  `src/sequencehelpers_p.cpp`（helper 本就为该单测导出），
  **测试源码零改动**。

## 2. 上游测试（R51 三步声明）

### 2.1 Step 1 — ctest 清单

```
$ ctest --test-dir <build_folder> -N
  Test #1: kglobalshortcuttest
Total Tests: 1
```

与上游默认构建（BUILD_RUNTIME=ON）的注册清单一致。证据：
`reports/upstream-test-inventory.txt`。

说明：上游另一个测试入口 `tests/kglobalacceltest`（QML 冒烟可执行文件）
上游本身就没有 add_test() 注册，不属于 ctest 清单。

### 2.2 Step 1.5 — 为什么配方内不做全量 ctest

构建沙箱内无 D-Bus session bus 时，`QDBusConnection::sessionBus()`
返回未连接连接，`interface()` 为 nullptr，上游 initTestCase 直接解引用会
段错误（探针证据 `reports/session-bus-probe.txt`：无 bus 时
`isConnected=0, iface=0`；有 bus 时 `isConnected=1, iface=0x…`）。
因此 build() 仅记录清单，全量执行在真机配好 session bus 后进行。

### 2.3 Step 2 — autotest 真机全量执行（kglobalshortcuttest）

环境：dbus-daemon 1.14.10（cmd-pkgs 预编译）以 abstract-socket 地址提供
session bus；OHOS 沙箱 uid 不在只读 /etc/passwd 中，dbus 启动需
getpwuid 垫片（LD_PRELOAD，仅测试环境，不入库）；Qt5DBus 为
dlopen("libdbus-1.so.3") 模式，需共享 libdbus（制品仓 dbus 包仅静态库，
用 dbus 1.14.10 源码原生编出共享库供测试运行时注入）。
被测二进制：conan create 构建树 `bin/kglobalshortcuttest`
（sha256 见 `reports/upstream-test-binary.txt`）。

```
PASS   : KGlobalShortcutTest::initTestCase()
QSYSTEM: Couldn't start kglobalaccel from org.kde.kglobalaccel.service:
         QDBusError("org.freedesktop.DBus.Error.ServiceUnknown", ...)
SKIP   : testSetShortcut() kglobalaccel not installed
SKIP   : testActivateShortcut() This test requires to be compiled with XCB-XTEST
SKIP   : testFindActionByKey() / testChangeShortcut() / testStealShortcut()
SKIP   : testSaveRestore() / testListActions() / testConfigurationActions()
SKIP   : testGetGlobalShortcut() / testForgetGlobalShortcut()   ← 同 "kglobalaccel not installed"
PASS   : testComponentAssignment()
PASS   : testNotification()
PASS   : testMangle() / testCrop() / testReverse() / testMatch()
PASS   : testOverrideMainComponentData()
PASS   : cleanupTestCase()
Totals: 9 passed, 0 failed, 10 skipped, 0 blacklisted, 2115ms
退出码: 0
```

完整日志：`reports/upstream-test-run.txt`（.log 依规不入库，已转
.txt 并脱敏：构建机内部路径泛化为 `<build_folder>` / aarch64 toolchain，
测试结论数据逐行保留）。

- **9 个 PASS 为真实断言**：initTestCase/cleanupTestCase（会话总线建立与
  清理）、testComponentAssignment/testNotification（公共 API 往返）、
  testMangle/testCrop/testReverse/testMatch（Utils 序列 helper 数学）、
  testOverrideMainComponentData。
- **10 个 SKIP 全部为上游自身的降级路径，技术原因明确**：
  - 8 个槽 QSKIP "kglobalaccel not installed"：initTestCase 对
    `startService("org.kde.kglobalaccel")` 的探测返回
    `org.freedesktop.DBus.Error.ServiceUnknown`，因为 kglobalacceld
    守护进程是 X11/XCB-only、在 OHOS 适配中排除（BUILD_RUNTIME=OFF）。
  - 1 个槽 QSKIP "This test requires to be compiled with XCB-XTEST"
    （testActivateShortcut）：X11 XTEST 注入路径，OHOS 不编译。

### 2.4 Step 2b — QML 冒烟可执行文件（上游无 ctest 注册）

`bin/kglobalacceltest` 正常启动，`KGlobalAccel::self()` 可用，因 QML 模块
缺失打印 `module "org.kde.kquickcontrols" is not installed` 后进入事件循环，
20s 超时 kill，退出码 124，无崩溃、无段错误（kquickcontrols 由
kdeclarative 提供，属上游循环依赖，非本包缺陷）。

## 3. test_package 消费者测试（R34）

6/6 断言通过（真实公共 API 往返，非 stub）：

```
PASS: KGlobalAccel::self() != nullptr
PASS: hasShortcut() is false before registration
PASS: hasShortcut() after setShortcut() equals the setShortcut() result
PASS: shortcut() returns at most the requested sequence
PASS: isGlobalShortcutAvailable() is idempotent for the same sequence
PASS: hasShortcut() is false after removeAllShortcuts()
PASS: kglobalaccel5 5.116.0 consumer test finished (6 assertions)
```

## 4. 已知平台伪影（不影响结果）

- 消费者测试运行时 QStandardPaths 打印 XDG_RUNTIME_DIR 属主警告：
  HMDFS stat 返回的 st_uid（20001006，文件管理器映射 uid）与进程
  getuid()（20020100）不一致所致，属平台固有问题；测试包已将
  HOME/XDG_RUNTIME_DIR 指向私有目录，断言不受影响。

## 5. 结论

| 项 | 结果 |
|---|---|
| conan create（构建 + 打包） | ✅ 成功 |
| 上游 ctest 清单 | 1（与上游默认构建一致） |
| 上游 autotest 真机执行 | 9 passed / 0 failed / 10 skipped，exit 0 |
| test_package 消费者测试 | 6/6 断言通过 |
| W3 本地 CI（L0/L1/L4/L5） | ✅ pass |

## 6. R40 适配完整性标注（需人工确认）

> **按 R40（深度适配库适配完整性验证）标注：需人工确认适配完整性。**

- **已验证**：库本体编译/链接/打包（SONAME、include、cmake config、
  D-Bus interface XML）、公共 API 行为（test_package 6 断言 + autotest
  9 个 PASS 中的公共 API 往返与序列 helper 数学）。
- **未验证**：核心注册路径——全局快捷键的端到端注册/激活由
  kglobalacceld 守护进程经 D-Bus 完成；守护进程为 X11/XCB-only，在
  OHOS 适配中排除（BUILD_RUNTIME=OFF），故该路径在本平台无端到端
  验证（autotest 中 8 个守护进程依赖槽位也因此走上游自身 QSKIP
  降级，非本包删减）。
- 消费者测试断言按 API 一致性设计（不依赖 D-Bus side effect），
  在 headless OHOS 上确定性通过，但**不证明**快捷键注册-激活链路
  在 OHOS 上的实际可用性。
