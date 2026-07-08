# TK 9.0.3.1 编译笔记（HarmonyOS PC · 标准 Conan Autotools）

## 定位
- 产出**动态** `libtcl9tk9.0.so`（供 dlopen，及作 CPython _tkinter 等的编译依赖），依赖 `tcl/9.0.3.1`。
- 源码 = **ohos_tk fork**（`9.0.3.1` 分支，OHOS 源码适配已 baked in）；用**标准 conan Autotools**
  构建（`unix/configure` + `make`），吃 CI profile 的原生 clang。

## 关键适配（都在 conanfile 里，均为 OHOS 原生构建暴露的坑）
1. **系统识别**：与 tcl 相同，tk 的 configure 也用 `uname` 判系统，HarmonyOS 不被识别。
   - configure 传 `tcl_cv_sys_version=Linux-6.6`（覆盖缓存，走 Linux 分支）；
   - build() 造 `uname` shim 报 Linux/aarch64 放 PATH 前。
2. **umask 077（E011）**：与 tcl 相同，HMDFS 上 `config.status` 硬编码 `umask 077` 导致权限问题。
   build() 把源码树内所有 configure 的 `umask 077` 替换成 `022`。
3. **`--with-tcl`**：指向 tcl 包的 libdir（找到 `tclConfig.sh`），Conan AutotoolsDeps 注入 tcl 的 -I/-L/-l。
4. **`--disable-zipfs`**：与 tcl 相同，避免脚本库 zip 尾拼破坏链接器自签。
5. **`--enable-ohos`**：tk fork 的 OHOS 适配选项，启用平台特定代码路径。
6. **X11 头文件**：tk.h `#include <X11/Xlib.h>`，但 autotools install-headers 只装公开 tk 头，
   不装源码 xlib/ 的 X11 stub 头。package() 把 `xlib/X11/*.h` 装进包 `include/X11/`。

## 产物
- `lib/libtcl9tk9.0.so`（动态库，干净 ELF + 链接器自签）
- `bin/wish`、`lib/tkConfig.sh`、`lib/libtkstub.a`、`include/*.h`、`include/X11/*.h`、`lib/tk9.0/`（散脚本库）

## 验证
- **上游测试（make test）**：在 build() 中尝试运行，编译失败。
  - 根因：`tktest` 二进制编译失败 — `tkIntPlatDecls.h` 仅在 `#if defined(WIN)` / `#if defined(X11)` 段内声明 `TkpTestsendCmd` 和 `TkpPrintWindowId`，OHOS 平台（`TK_OHOS=1`）不满足任一条件，导致 `tkTest.c` 引用未声明标识符。
  - OHOS fork 的 `ohos/tests/` 有自带纯算法单测（`test_tkOhosCompute` 58/58 通过），但非标准 `make test` 目标。
  - build() 中用 try/except 捕获失败，不阻塞构建。
- **test_package**：
  - **C 级用户测试**（test.c）：链接 libtcl9tk9.0 + libtcl9.0，调用 C API：
    - `Tcl_CreateInterp()` → 解释器创建 ✅
    - `Tcl_Init()` → Tcl 运行时初始化 ✅
    - `Tk_Init()` → Tk 运行时初始化 ✅
    - `Tcl_GetVar("tk_version")` → `9.0` ✅
    - `Tcl_GetCommandInfo("toplevel")` → 命令已注册 ✅
    - 使用 `_exit(0)` 避免 OHOS 系统库 atexit 悬空
  - R34：test_probe 链接 libtcl9tk9.0（NEEDED），调用 Tk C API 验证库可加载且运行时可初始化。
  - L1e 破坏性反向验证：移走 lib/ 后动态链接器找不到 libtcl9tk9.0.so → test_probe 启动失败 → test 确实依赖 tk。
- **dlopen segfault 根因**：dlclose(libtcl9tk9.0.so) 卸载库时，OHOS 系统依赖库（libace_napi.z.so 等）的 atexit 处理器变为悬空指针，进程退出时调用已 unmap 的代码 → SIGSEGV。wish9.0 以链接方式加载库（非 dlopen），库在进程整个生命周期内常驻，atexit 处理器可正常执行，故不 segfault。
- conan-verify：G0-G4 + L2/L4/L5 全部 PASS（2026-07-08）

## 依赖
- `tcl/9.0.3.1`（已发布到制品仓 ohpcd）

## 知识提取
- tk 的适配坑与 tcl 基本一致（uname shim、umask 077、--disable-zipfs）。
- 额外点：tk.h 依赖 X11 stub 头，需在 package() 中手动复制 xlib/X11/*.h 到 include/X11/。

---
**状态**：built（conan-verify 全门禁通过 + CI 本地模拟通过，待 CI upload 后标 published）
