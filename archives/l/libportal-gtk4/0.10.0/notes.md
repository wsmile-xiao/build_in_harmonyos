# libportal-gtk4 0.10.0 适配笔记

## 软件简介
libportal-gtk4 是 libportal（Flatpak 团队的 XDG 桌面门户库）的 **GTK4
backend 变体**：在同一上游源码树（https://github.com/flatpak/libportal，
Meson 构建，C 语言）上以 `-Dbackend-gtk4=enabled` 构建，产物为
`libportal-gtk4.so`（XdpGtk4 父窗口句柄导出 backend，核心 API
`xdp_parent_new_gtk(GtkWindow*)`）+ `libportal-gtk4.pc`（Requires: gtk4,
libportal）+ 头文件 `libportal-gtk4/portal-gtk4.h`。

上游同版本归档：`archives/l/libportal/0.10.0`（gtk3 backend 变体，
backend-gtk4=disabled）。本包为独立 conan 包名 `libportal-gtk4`，两包
可并存（`.so`/`.pc`/头文件路径均不冲突）。

## 上游版本确定
- tag 0.10.0（与 libportal/0.10.0 同一 release tarball）
- 官方 release tarball：
  `https://github.com/flatpak/libportal/releases/download/0.10.0/libportal-0.10.0.tar.xz`
  sha256=`1c74a3f7becbd4ff745d7f565afd06e97e50eb080a0e268cb14bb55289a745bf`（实测）

## 依赖解析（W0 已核验制品仓，全部命中）
| 上游模块 | Conan 包 | 说明 |
|---|---|---|
| glib-2.0 / gio-2.0（>=2.80）/ gio-unix-2.0 | `glib/2.84.0.1.1` | 核心库唯一链接依赖（GDBus 客户端，构建期不需要运行时 bus） |
| gtk4（dependency('gtk4')） | `gtk4/4.22.4` | backend-gtk4，传播给下游 |

**glib 版本对齐（关键决策）**：gtk4/4.22.4 配方
`requires("glib/2.84.0.1.1", override=True)` 钉死其闭包。本包若用
`glib/2.84.0.1` 会出现同一闭包两个 glib 版本的版本冲突——因此本包
也钉 `glib/2.84.0.1.1`（conan download 实测制品仓已有该 revision）。

`gio-unix-2.0.pc` / `gtk4.pc` 由包内 `lib/pkgconfig` 经
`_append_dependency_pkg_config_paths()` 注入 meson `pkg_config_path`
（glib conan 配方只声明 gio-2.0 组件，PkgConfigDeps 不生成
gio-unix-2.0.pc——libportal/accountsservice 同款处理）。

`gnome.mkenums`（portal-enums.c/h 生成）需要 glib-2.0.pc 的
`glib_mkenums`/`glib_genmarshal`/`gobject_query` 变量——配方
`_augment_glib_pkg_config()` + python wrapper 处理（libportal 同款）。

## 构建配置
```
-Dbackend-gtk4=enabled    （本包核心交付；gtk4/4.22.4 仓内✅）
-Dbackend-gtk3=disabled   （gtk3 backend 属 libportal/0.10.0 包）
-Dbackend-qt5=disabled    （OHOS 无 qt5）
-Dbackend-qt6=disabled    （OHOS 无 qt6）
-Dintrospection=false     （无 g-ir-scanner 工具链）
-Dvapi=false              （无 vapigen）
-Ddocs=false              （无 gi-docgen）
-Dtests=false             （见下）
-Dportal-tests=false      （demo 应用，不交付）
```

### 平台要点（XDG portal 的 DBus 依赖）
- libportal 是纯 **GDBus 客户端**库：所有 portal 交互走
  `g_dbus_connection_call*`，构建/安装阶段不需要 session bus 存在。
- portal-gtk4.c 的 X11/Wayland 代码全部在 `#ifdef GDK_WINDOWING_X11`/
  `#ifdef GDK_WINDOWING_WAYLAND` 守卫内；仓内 gtk4/4.22.4 是 broadway
  flavor（`gdkconfig.h` 只定义 `GDK_WINDOWING_BROADWAY`），两段代码自然
  编译排除，**无需平台补丁**（R1 参数最少化原则：0 个源码补丁）。
- `sys/vfs.h`：OHOS SDK sysroot 提供（libportal 同源码已实测）。
- 源码无平台硬编码路径/dlopen/bashism（G0 预扫描通过，同源码）。

## 上游测试（N=81，pytest 套件，环境豁免 + 本机真实执行结论）
上游测试套 `tests/pyportaltest/` 共 81 个 pytest 用例（inputcapture 35、
notification 13、remotedesktop 19、screencast 6、wallpaper 8）+ qt5/qt6
各 1 个 meson test 目标。

上游测试与 backend 无关（全部走 GI 绑定调核心 Xdp* API），
libportal/0.10.0 归档已在本机完成全环境真实执行（reports/upstream-test-report.md）：
- **81/83 真实执行，66 通过 15 失败（81.5%）**；qt5/qt6 2 例不注册豁免
- 15 例失败单一根因：OHOS unix-fd（SCM_RIGHTS）句柄投递平台语义差异
  （9 例 negative file descriptor / 3 例 mock 端 fdlist MemoryError /
  4 例 notification icon file-descriptor 变体）——非库缺陷
- 环境链：conan dbus-daemon（TCP）+ python-dbus + dbusmock + PyGObject
  + Xdp-1.0.gir（同源码 -Dintrospection=true 构建）；本包源码与
  libportal/0.10.0 完全相同（同一 tarball），该结论直接适用

CI（远端 clean 环境）无 dbus/dbusmock/PyGObject/GI 环境，三个前置均
不成立（meson `tests/meson.build` 探测 python 模块缺失时静默跳过注册
——上游自身的条件跳过路径），故配方 `-Dtests=false`，功能覆盖由
test_package L1 测试补偿（R51 口径：上游测试三步法已在同源码归档完成，
本包引用其结论与证据）。

## test_package（L1 消费者测试，无 bus/无 display 确定性断言）
test_libportal_gtk4.c 调用真实 API：
1. `gtk_get_major_version()`：真实 GTK4 运行时调用（纯版本查询，无需
   display）——证明 libportal-gtk4.pc 的 Requires: gtk4 链接加载成功
2. `xdp_parent_new_gtk` 符号解析：函数指针绑定（不调用——需活动
   GtkWindow/display），验证 libportal-gtk4 backend 库已链接且导出
3. portal-gtk4.h + gtk4 头文件 include 编译通过（含 GDK_WINDOWING 守卫集）
4. 核心 XdpPortal 类型系统注册（GObject 链）
5. `xdp_portal_running_under_flatpak/sandbox()` == FALSE（确定性探测）
6. `xdp_portal_initable_new()` 无 session bus 时按文档语义返回
   NULL + GError（上游推荐的安全失败路径）

## 环境坑（继承 libportal 归档经验，配方已防御）
本机 shell 的 `LD_LIBRARY_PATH` 含带空格损坏条目
（`chipset-pub-sdk:<空格>/system/lib64`）：动态链接器解析失败 → meson
探测 ninja 失败。配方在 `_build_environment()` 前置干净的
`/system/lib64`：对健康 CI worker 是 no-op，对损坏 session 是修复。

## 构建结果
（W3/finish 后回填）
- conan create（ohos-aarch64 profile，shared=True）：
- 产物：libportal.so / libportal-gtk4.so（已 ELF 签名）、公共头、
  libportal.pc / libportal-gtk4.pc
- test_package：编译、链接、运行

## Reproduce True-Device Command
```sh
export PATH=/data/service/hnp/ninja.org/ninja_1.13.1/bin:/data/service/hnp/bin:$PATH
cd archives/l/libportal-gtk4/0.10.0
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
```
---

**编译结束**: 2026-09-23 17:57
**最终状态**: built
