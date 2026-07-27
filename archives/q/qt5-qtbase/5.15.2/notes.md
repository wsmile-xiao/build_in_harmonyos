# qt5-qtbase 5.15.2 适配笔记

## 编译环境
- 构建系统: configure + make
- 编译日期: 2026-07-02
- 编译器: clang/clang++ 15.0.4
- 状态: built（Gui/OpenGL 扩展待 CI 验证）

## 关键适配

### 1. Qt5Test 模块
原始配置 `-no-feature-testlib` 禁用了 Test 模块。去掉此选项后重新 configure，
使 Qt5Test 库可用（qtremoteobjects 上游测试依赖）。

### 2. 抽象套接字补丁 (E216)
OHOS 不允许文件式 Unix 域套接字 `bind()`（Operation not permitted）。
补丁 `qlocalserver_unix.cpp` 和 `qlocalsocket_unix.cpp` 使用抽象套接字命名空间
（`sun_path[0]='\0'` + `memset` 清零），绕过文件系统限制。

### 3. 禁止 strip (E215)
OHOS musl 动态链接器拒绝 dlopen stripped ELF（Permission denied）。
设置 `QMAKE_STRIP=""` 禁止 strip，保持库文件包含 .symtab 节区。

### 4. libz.so
libQt5Core.so 依赖 libz.so，OHOS 系统中不存在。通过 Conan 依赖
`zlib/1.3.1` 提供共享库、头文件和链接路径。

## 验证结果
- 待 CI 验证: libQt5Core/Gui/Network/Test/Concurrent + libz.so (全部未 strip)
- ✅ qtremoteobjects 19 个上游测试中 7 个模块通过 (144 个用例 PASS)
- ✅ 抽象套接字补丁使 local socket IPC 在 OHOS 上工作

### 5. Qt3D 依赖补全

启用 QtGui 与 OpenGL ES 2，保留无窗口平台配置，向 qt3d 提供 qmake、moc、
Qt5Core、Qt5Gui 和 Qt5Network。构建由 `-j1` 调整为受控的 `-j4` 并行，
避免完整 Qt Base 构建超过 CI 的 45 分钟硬限制。

### 6. OHOS qmake 宿主环境

`QMAKE_HOST.os` 直接取 `uname().sysname`，OpenHarmony 的返回值不在 Qt 5.15.2
白名单中。对已知平台分支之外的 `Q_OS_UNIX` 宿主使用 `LD_LIBRARY_PATH`，
使构建期 qmake 工具能够加载 Qt 共享库。
