# qtserialport-opensource-src 5.15.15 适配笔记

- 软件：qtserialport-opensource-src 5.15.15（Qt 5 串口通信模块）
- 构建系统：qmake（上游 .pro，`QT = core-private`）
- 依赖：qt5-qtbase/5.15.2.2（制品仓已发布）
- 产物：libQt5SerialPort.so（含 .prl/.pc/mkspecs/cmake config）
- libudev：qt5-qtbase 配置为 disabled（qmodule.pri），串口枚举走 /sys/class/tty 回退，无额外依赖

## 根因与修复（第 2 次尝试，PR #7779 CI 修复）

CI 失败 `Project ERROR: Unknown module(s) in QT: core-private` 根因：
qt5-qtbase 制品仓包内 `bin/qt.conf` 与 `mkspecs/modules/*.pri` 残留原构建机的
conan 缓存绝对路径（`~/.conan2/p/b/qt5-qXXXX/b`），在任何其他缓存位置
（CI 为 `~/.cache/conan2`）均为悬空路径，qmake 无法加载 modules-inst 下的
模块定义（core/core-private 等）。

修复方式＝仓库内已验证 Qt5 模块先例（qt5-qtdeclarative/5.15.2、
qt5-qtsvg/5.15.2.1、qt5-qtcharts/5.15.2.1，均依赖 qt5-qtbase/5.15.2.2 且 CI 绿）：
- `_fix_qtbase_paths()`：重写 qtbase 包内 qt.conf 指向当前包目录；
  正则重写 mkspecs/{modules,modules-inst}/*.pri 中构建机路径 → 当前包目录
- build()：`cd source_folder && qmake -spec linux-clang qtserialport.pro` +
  `make -j{jobs} QMAKE_STRIP=""`（OHOS loader 拒绝 strip 后的 ELF）
- 移除第 1 次尝试的 symlink/qt.conf+modules-inst 复制 hack（向 ~/.conan2
  创建符号链接与目录，跨缓存不可靠且污染包外状态）

test_package 失败（`Qt5CoreConfigExtras.cmake` 引用 `../b//mkspecs` 悬空路径）
根因：qtbase 包内自带 lib/cmake 同样有构建机残留路径。修复＝qtcharts 先例：
CMakeDeps 直接依赖场景生成聚合 config（find_package(Qt5) → Qt5::Core；
find_package(qtserialport-opensource-src) → Qt5::SerialPort），完全避开
qtbase 包内 cmake 文件；test() 手动设 LD_LIBRARY_PATH。

## 上游测试清点与实测（R51）

上游 tests/ 共 4 个 auto 测试工程（qmake，无 ctest 注册）：
- tests/auto/qserialport（tst_qserialport）
- tests/auto/qserialportinfo（tst_qserialportinfo）
- tests/auto/qserialportinfoprivate（需 serialport-private，随包构建验证）
- tests/auto/cmake（仅 CI 用 cmake 消费验证，与 conan test_package 重复）

实测（本机 HarmonyOS PC，原生运行）：
- tst_qserialport：1 passed, 0 failed, 1 skipped —— initTestCase QSKIP：
  需要 QTEST_SERIALPORT_SENDER/RECEIVER 指向物理串口对（无硬件环境的具体技术
  原因，非"没环境"）
- tst_qserialportinfo：1 passed, 0 failed, 1 skipped —— 同上
- conan test_package（L1）：test_qtserialport 运行通过，QSerialPort/
  QSerialPortInfo API 构造/枚举/baudRate 断言全过（0 个物理串口，枚举为空）
- tests/auto/qserialportinfoprivate：上游开发者测试（需 serialport-private 模块），
  随包 mkspecs modules-inst 提供 private pri，不单独运行

⚠️ R40 适配完整性（外设类，待人工确认）：适配为实质性——上游原生
termios I/O 与 /sys/class/tty 枚举代码路径真实编译执行（无 stub/平台宏），
但无物理串口对环境下真实串口 open/read/write 数据收发未验证。有硬件时
设置 QTEST_SERIALPORT_SENDER/RECEIVER（如 ttyS0/ttyS1 回环）可全量运行
上游测试，建议合入后在带串口的鸿蒙 PC 上补测。

## 修复历史
- v1: qmake 找不到 qtserialport.pro → source_folder 绝对路径
- v2: core-private 未知模块 → qt.conf + symlink hack（CI 未过，本机可复现失败）
- v3（本次）: 先例对齐重写（qt.conf+.pri 重写、QMAKE_STRIP=""、CMakeDeps
  test_package），本地 conan create 全绿（lib 构建 + 上游 2 测试 + L1 测试）

**最终状态**: built（本地 conan create EXIT=0，待 CI 复验）
---

**编译结束**: 2026-09-18 09:17
**最终状态**: built
