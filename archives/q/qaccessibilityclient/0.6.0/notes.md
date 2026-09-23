# notes — qaccessibilityclient 0.6.0 (HarmonyOS PC)

## 身份与来源

- 上游: https://invent.kde.org/libraries/libqaccessibilityclient（KDE Accessibility 组）
- 归档: https://download.kde.org/stable/libqaccessibilityclient/libqaccessibilityclient-0.6.0.tar.xz
- SHA256: 4c50c448622dc9c5041ed10da7d87b3e4e71ccb49d4831a849211d423c5f5d33（设备端 sha256sum 实算）
- 0.6.0 为上游最新 tag（2023-12-03），Qt6 分支要求 Qt >= 6.5，导出
  CMake 包名 QAccessibilityClient6 / 目标 QAccessibilityClient6 /
  库文件 libqaccessibilityclient-qt6.so（SOVERSION 0）
- license: LGPL-2.1-only OR LGPL-3.0-only（LICENSES/ 目录 + 源头注释）

## 为什么是这个版本

accessibility-inspector 26.04.3 硬依赖 `find_package(QAccessibilityClient6
0.6.0 CONFIG)`（TYPE REQUIRED），0.6.0 恰好满足且为最新官方发布。

## 适配要点

1. `QT_MAJOR_VERSION=6` 由配方显式传入 —— 上游自身不做 Qt5/Qt6 检测。
2. `KF_IGNORE_PLATFORM_CHECK=TRUE`（OHOS 不在 KDE 平台列表）。
3. 依赖面收敛为 `qtbase/6.11.1.1`（Widgets/DBus/Test 组件齐备，E323）+
   `extra-cmake-modules/6.29.0`（tool）。
4. ECM_MODULE_PATH 手工注入、`conan_cmakedeps_paths.cmake` 手工生成
   （qtbase cmake_find_mode=none 的既定处理，kdbusaddons 6.29.0 同款）。
5. `QUERY_EXECUTABLE=qtpaths6` 直指 qtbase 包内二进制（ECMQueryQt 的
   Qt6CoreTools 不被 Qt6Config 加载，mobipocket 先例）。

## 上游测试

- `tests/auto/tst_accessibilityclient`（QtTest，唯一自动化入口；
  simplewidgetapp 为其辅助进程）。BUILD_TESTING=ON 时经 ctest 在
  build() 内真实运行（offscreen QPA，--timeout 90）。
- 本机实测结果：**5 passed / 6 failed**（4263ms，Totals 行）。
  - 通过：cleanupTestCase 等 + 纯逻辑槽（tst_registry /
    tst_accessibleObject / tst_hashable）。
  - 失败槽全部为同一环境根因：`"Not connected to D-Bus server"` ——
    tst_application / tst_navigation / tst_focus / tst_states /
    tst_extents / tst_characterExtents 需要活动 AT-SPI2 a11y 总线。
- a11y 总线不可得的穷尽证据（设备实测 2026-09-03/04）：
  1. 制品仓 dbus/1.14.10 只含 include/ + lib/（无 dbus-daemon /
     dbus-run-session 二进制）；系统 /usr/bin、/system/bin 也无 dbus*。
  2. 制品仓 at-spi2-core/2.60.5 提供 at-spi-bus-launcher /
     at-spi2-registryd 与 org.a11y.Bus.service，但两者都必须先有
     D-Bus daemon 才能拉起 → 无法启动。
  3. 即便总线/registry 可用：已发布 qtbase/6.11.1.1 的 plugins/ 下无
     accessibilitybridges/（Qt AT-SPI 桥插件未随包发布），Qt 应用无法
     把自己的无障碍树发布到 AT-SPI 总线，6 个树浏览槽仍会得到空树。
     补齐需重制 qtbase（atspi2 桥）+ dbus daemon 变体，超出本包范围。
- 结论：可运行子集已真实运行并记录；总线依赖子集为平台能力阻塞，
  按 karchive/kdbusaddons 先例不阻塞包创建。

## 关键工程发现（E537 类，链接期 soname）

- OHOS 的 CMake HarmonyOS 平台模块不定义 SONAME flag → 共享库无
  DT_SONAME，消费者按路径记录 DT_NEEDED（本仓多库已知问题 E537）。
- 实测 `/data/service/hnp/bin/clang++` 支持 `-Wl,-soname` 且正常输出
  SONAME；配方通过 CMAKE_SHARED_LIBRARY_SONAME_{C,CXX}_FLAG 在链接期
  打开 → 本包产物 libqaccessibilityclient-qt6.so 带 SONAME
  `libqaccessibilityclient-qt6.so.0`，消费者记录裸名。
- patchelf 后处理与签名的准确边界（2026-09-04 归档探针更正，
  reports/builder/probe-soname-sign/）：工具链在链接期对产物自签名，
  naive patchelf（改后不重签）→ `Operation not permitted` (rc=126)；
  未先 remove-section .codesign 直接重签 → `.codesign section already
  exists` → SignElf 29（E077 forbid_2 已记载的失败模式）；按 E077 四步
  流程（remove-section → patchelf → sign -selfSign 1 → chmod）改写后
  exec/dlopen 正常。链接期修复仍是首选（producer 侧泛化、免逐产物
  重签），E077 流程为合规 post-link fallback。

## CI 与上游测试结果（权威 CI，ci/conan/build_and_test.sh）

- CI_RC=0：G0/L0/L1(upstream+test_package)/L4/L5 全过；L2 skip
  （examples/dumper 示例二进制 version/help 失败，非阻塞）。
- L1c：build() 内 ctest 真实执行记录（5 passed / 6 failed，见上节）。
- test_package：find_package(QAccessibilityClient6) + 链接裸导出目标
  QAccessibilityClient6 + Registry headless-safe 断言，rc=0。

## 运行时边界

本库经 D-Bus 连接 AT-SPI2 总线读取"其它应用"的无障碍树；鸿蒙 PC 无
桌面 a11y 总线时 Registry 侧 API 可用（连接/订阅/缓存逻辑），树内容为
空。消费者（accessibility-inspector）需用户级拉起 dbus + at-spi2-core
才能看到内容。
