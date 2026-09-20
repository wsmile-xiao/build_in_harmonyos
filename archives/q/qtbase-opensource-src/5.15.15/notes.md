# qtbase-opensource-src 5.15.15 适配笔记

## 编译环境
- 构建系统: configure + make
- 编译日期: 2026-08-27
- 编译器: clang/clang++
- 状态: built
- conan-verify: PASSED (G0-G4 all gates)

## 概述

本包为 Qt 5 Base 模块在 OpenHarmony PC 平台的适配。包含 Core, Gui, Network,
Test, Concurrent, OpenGLExtensions, DBus, Widgets, PrintSupport, Xml 等全部模块
库，以及 qmake, moc, rcc 等开发工具。

## 关键适配

### 1. 抽象套接字补丁 (E216)
OHOS 不允许文件式 Unix 域套接字 `bind()`（Operation not permitted）。
补丁 `0001-abstract-socket.patch`（QLocalServer）和
`0002-abstract-socket-client.patch`（QLocalSocket）使用抽象套接字命名空间
（`sun_path[0]='\0'` + `memset` 清零），绕过文件系统限制。

R8 改造后，抽象套接字补丁为无条件启用（Linux/OHOS 内核均支持 AF_UNIX
抽象套接字），不再按目标平台切换编译期分支。

### 2. pthread_cancel 守卫 (0003)
OHOS musl 不提供 `pthread_cancel`。补丁在 Qt 源码中添加
`HAVE_PTHREAD_CANCEL` 守卫，配方在 build() 阶段通过 feature detection
脚本检测编译器是否支持 `pthread_cancel`，仅在检测通过时定义该宏。

### 3. socklen_t 修复 (0004)
OHOS musl 的 `socklen_t` 类型与 glibc 不同。补丁统一使用 POSIX 标准的
`socklen_t` 类型，兼容现代 Linux 和 OHOS 目标。

### 4. qmake OHOS 宿主支持 (0005)
`QMAKE_HOST.os` 直接取 `uname().sysname`，OpenHarmony 的返回值不在 Qt
白名单中。补丁对已知平台分支之外的 `Q_OS_UNIX` 宿主使用
`LD_LIBRARY_PATH`，使构建期 qmake 工具能够加载 Qt 共享库。

### 5. 禁止 strip (E215)
OHOS musl 动态链接器拒绝 dlopen stripped ELF（Permission denied）。
设置 `QMAKE_STRIP=""` 禁止 strip，保持库文件包含 .symtab 节区。

### 6. Qt5DBus
配置 `-dbus` 启用 Qt5DBus 模块，依赖 `dbus/1.14.10`。libngf-qt 等
QtDBus 消费者需要此模块。

### 7. 测试兼容性补丁 (0006-0011)
- 0006: QtSql 基准测试在禁用 QtSql 时跳过
- 0007: OHOS 不提供 pthread_yield，改用 POSIX sched_yield
- 0009: Clang 下保持插件指针段类型一致
- 0010: 使用标准浮点异常标志替代非标准 feenableexcept
- 0011: 同步 QThreadPool 并发峰值测量与工作线程启动

## 模块依赖关系
- zlib/1.3.1: libQt5Core 依赖 libz
- dbus/1.14.10: libQt5DBus 依赖 libdbus-1
- EGL/GLESv2: libQt5Gui 依赖系统 OpenGL ES 库

## 验证结果
- conan create: SUCCESS (Qt 5.15.15 编译成功)
- conan-verify: PASSED (G0-G4 全部门禁)
- test_package: PASSED (Qt5 Widgets/PrintSupport/Xml 组件链接+运行验证)

## 恢复说明
本 PR 的配方和补丁从 conan 缓存恢复
(`/storage/Users/currentUser/.conan2/p/qtbas779c64c118ac3/`)。
仓库重新克隆后丢失了 feature branch，但 conan 包缓存完好无损，
conan-verify 全部门禁通过 (G0-G4)。

---

**编译结束**: 2026-08-27 23:45
**最终状态**: built

## 2026-09-17 CI 修复（PR #7097 重试）

### 故障
CI #40001（2026-09-05）在 conan-build-test 步骤失败：
`ConanException: Failed to apply patch: 0011-qthreadpool-ohos-startup-sync.patch`
hunk 3 期望 `for (int i = 0; i < 20; ++i)`，而纯净源码该处（首循环，
tst_qthreadpool.cpp:807）为 `4*QThread::idealThreadCount()`（仅第二处循环为 20）。

### 根因
补丁是在**已被手工预编辑过的源码树**上生成的（预编辑把首循环改成了 20，
但该改动未沉淀为补丁）。当时本地 conan-verify 未拦截：配方是从 conan 缓存
（`~/.conan2/p/qtbas779c64c118ac3/`）恢复的，缓存中的 source 目录已含历史
改动，掩盖了补丁与纯净源码的偏差；干净环境的 CI 一跑即暴露。

### 修复
- 仅修正 hunk 3 的一行上下文（`20` → `4*QThread::idealThreadCount()`），
  补丁语义不变（QSemaphore 同步峰值并发测量）。
- 用 patch_ng（conan 同款补丁器）对**纯净 tarball** 全量验证 10 个补丁
  全部可应用。
- `ci/config/build_timeouts.txt` 登记 `qtbase-opensource-src/5.15.15 14400`
  （与 Buildbot 步骤 4h 预算对齐）。
- 本地 W3（ci/conan/build_and_test.sh，与 CI 同脚本）复验通过后推送。

### 教训
从 conan 缓存恢复配方后，必须对**全新解压的官方 tarball** 重放补丁验证，
不能信任缓存 source 目录的状态。

