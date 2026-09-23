# Draft: pkg_check_modules REQUIRED 系统级依赖缺失 → CMake 可选选项 + #ifdef 编译开关 + stub

> Status: DRAFT | Source: ayatana-indicator-messages 24.5.2 (OpenHarmony PC), PR 待提交 | 原则: 无
> 严重度: 🟡 medium | 分类: dependency/pkgconfig/cmake/system-daemon/stub | 自动修复: ✅ patch + conanfile 选项

> **结构化数据**: [graph](../knowledge/graph/DRAFT-ayatana-accountsservice-required-dep-optional-stub.kv) 对应 draft .kv

---

## 错误特征

```
CMake Error at CMakeLists.txt:XX (pkg_check_modules):
  Package 'accountsservice' not found
The pkg-config script "accountsservice.pc" could not be found
-- Checking for modules 'glib-2.0>=2.36;gio-unix-2.0>=2.36;accountsservice'
--   Found glib-2.0 ... ; Found gio-unix-2.0 ... ; accountsservice: not found
```

（配套：`find_package(GSettings)`/`add_schema`、`find_package(Intltool REQUIRED)`、
`find_package(GObjectIntrospection REQUIRED)`/`find_package(Vala REQUIRED)`、
gtkdoc-scan 等桌面集成依赖缺失时的 configure 失败。）

## 根因

- Ayatana/GNOME 系桌面服务（indicator 家族）把系统守护进程的**客户端库**（如
  accountsservice，即 AccountsService 的 libact 客户端）以及 GSettings/Intltool/
  gtk-doc/GObjectIntrospection/Vala 列为 `pkg_check_modules REQUIRED` / `find_package REQUIRED`
  依赖；
- HarmonyOS 制品仓无 accountsservice 配方、无 AccountsService 守护进程（用户/会话管理由
  OHOS 自身机制承担），也无 GSettings/Intltool/gtk-doc/GI/Vala 桌面工具链；
- REQUIRED 语义下任一缺失即 configure 失败，且这些依赖服务于**桌面会话集成特性**
  （draws-attention、greeter 显示、桌面绑定数据），非服务主体运行必需。

## 首错（First Error）

顶层 CMakeLists `pkg_check_modules(PROJECT_DEPS REQUIRED ... accountsservice)` 中
accountsservice.pc 缺失 → CMake configure 直接失败（早于任何编译）。

## 诊断顺序（Diagnosis Order）

1. `grep -n "pkg_check_modules\|find_package" CMakeLists.txt */CMakeLists.txt` 列出全部
   REQUIRED 依赖；
2. `conan search "<dep>*" -r ohpcd` + 仓库 `archives/` 确认依赖是否有配方/制品；
3. 对无配方的依赖逐个判定「是否服务主体必需」：
   - 必需（glib/gio-unix）：保留 REQUIRED，用 PkgConfigDeps + 手工补 .pc 解决；
   - 桌面集成可选（accountsservice/GSettings/Intltool/gtk-doc/GI/Vala）：降级为
     CMake 可选选项，关闭时裁剪。

## 失败替代方案（Fallback）

若依赖确为服务核心（如 dbus 主循环），不能裁剪——此时须先适配依赖本身（另开 PR），
或换用替代实现；不伪造 .pc / 空库来骗过 configure。

## 验证边界（Validation Boundary）

- 关闭选项后 configure 必须通过，且 `cmake --build` 全程无 `unable to find library` /
  `No rule to make target` 等残留引用；
- stub 路径必须保证对外符号齐全（`nm` / 链接成功），行为退化需在 notes.md 如实说明；
- 服务可执行文件在 conanrun 环境下能启动（test_package 冒烟，exit ≠ 127）。

## 解决方案

1. **顶层 CMakeLists**（0001 补丁）：
   - `option(ENABLE_ACCOUNTS_SERVICE "..." ON)` / `option(SKIP_DATA_PO ...)` /
     `option(SKIP_DOC ...)`；
   - `pkg_check_modules(PROJECT_DEPS REQUIRED glib-2.0 gio-unix-2.0)` 只留真实依赖；
   - `if(ENABLE_ACCOUNTS_SERVICE) pkg_check_modules(ACCOUNTS_SERVICE REQUIRED accountsservice);
     list(APPEND PROJECT_DEPS_INCLUDE_DIRS ...); list(APPEND PROJECT_DEPS_LIBRARIES ...);
     add_definitions(-DHAVE_ACCOUNTS_SERVICE=1) endif()`；
   - `if(SKIP_DATA_PO) ... else() add_subdirectory(data) add_subdirectory(po) endif()`，
     doc/ 同理。
2. **源文件 stub**（0002 补丁）：im-accounts-service.c 以 `#ifdef HAVE_ACCOUNTS_SERVICE`
   包裹 `#include <act/act.h>` 与真实实现；`#else` 分支编译 stub（含 `#include <gio/gio.h>`），
   ref_default 返回空 GObject、set_draws_attention no-op、get_show_on_greeter 恒 FALSE。
3. **libmessaging-menu**（0003 补丁）：`option(ENABLE_INTROSPECTION ...)` 包裹
   GObjectIntrospection/Vala 的 gir/typelib/vapi 生成（桌面语言绑定非核心）。
4. **链接目录**（0004 补丁）：pkg_check_modules 把 `-L` 放在 `*_LIBRARY_DIRS`、只把 `-l`
   放进 `*_LIBRARIES`——`target_link_directories(${PROJECT_DEPS_LIBRARY_DIRS})` 补上，
   否则 ld.lld `unable to find library -lgio-2.0/-lglib-2.0/-lpcre2-8` 等。
5. **conanfile.py**：`tc.variables["ENABLE_ACCOUNTS_SERVICE"]="OFF"`、`SKIP_DATA_PO="ON"`、
   `SKIP_DOC="ON"`、`ENABLE_INTROSPECTION="OFF"`、`ENABLE_TESTS="OFF"`；另用
   `CMAKE_PROGRAM_PATH` 钉死 glib bin（避开 SDK 坏 gdbus-codegen）、LD_LIBRARY_PATH 前置
   SDK llvm/lib（lld 加载 libxml2.so.16）。

## 跨库复用价值

- **Ayatana indicator 家族**（display/session/messages/a11y/power）共用同一套
  pkg_check_modules 桌面依赖模式，本方案可整体复制；
- 任何 GNOME 系服务依赖 accountsservice/GSettings/Intltool/gtk-doc 时同法裁剪；
- 「REQUIRED 依赖缺失 → 选项降级 + 编译开关 + stub」是通用的依赖裁剪诊断模式。
