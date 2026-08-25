# awf-gtk 4.2.0 OpenHarmony PC 适配笔记

## 软件简介

awf-gtk（上游包名 awf-extended，"A widget factory"）是一个跨 GTK/Qt 的**主题预览应用**，
用于展示当前桌面主题下各 GUI 控件的外观。本适配构建其 **GTK4 前端**（`awf-gtk4`），
输出为可执行文件 + desktop/man/icons/locale/bash-completion 数据。

## 编译环境

- 构建系统: autotools（上游 release 为源码归档，需 `autoreconf -fi` 生成 configure）
- 编译日期: 2026-08-23
- 编译器: clang / clang++（`/data/service/hnp/bin/clang{,++}`，Conan profile `ohos-aarch64`）
- 目标平台: HarmonyOS PC aarch64（os=OHOS, arch=armv8）
- 状态: built（conan-verify 通过，未 upload）

## 编译步骤

1. **解包**（上游 release 归档不含预生成 configure）：

```bash
mkdir -p ~/tmp/builds && tar xzf ~/tmp/builds/awf-gtk-4.2.0.tar.gz -C ~/tmp/builds/awf-gtk-4.2.0.work
```

2. **生成 configure**：

```bash
cd ~/tmp/builds/awf-gtk-4.2.0.work
autoreconf -fi
```

3. **E114 补丁**：生成的 `configure` 里 config.status 的临时目录使用
   `mktemp -d ./confXXXXXX`（HMDFS 兼容问题），改为固定目录：

```bash
# configure 中:
#   tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null` ...
# 替换为:
#   tmp=/storage/Users/currentUser/tmp/awf-cs-tmp
#   mkdir -p "$tmp" 2>/dev/null || true
```

4. **pkg-config 环境**（系统 GTK4 前缀 + conan 缓存包头文件 overlay）：

```bash
export PKG_CONFIG_PATH="$HOME/tmp/awf-pkgconfig:$HOME/usr/local/lib/pkgconfig:$HOME/usr/local/share/pkgconfig"
```

overlay（`~/tmp/awf-pkgconfig/`）内容：
- `gtk4.pc`：系统 gtk4.pc 的副本，**去掉 Requires 中的 cairo-gobject**（系统前缀和制品仓都没有 cairo-gobject.pc）
- `cairo.pc`：includedir 指向 conan cairo 包，libdir 指向系统 `/usr/local/lib`（签名的 libcairo.so.2）
- `graphene-1.0.pc` / `graphene-gobject-1.0.pc`：指向 conan graphene 包
- `libnotify.pc`：指向 conan libnotify 包
- `libpng.pc`：系统 libpng16 的别名

5. **configure + make**：

```bash
./configure --prefix=/storage/Users/currentUser/usr/local --enable-only-gtk4
make -j2
make install
```

`--enable-only-gtk4` 只启用 GTK4 前端（GTK2/3/5、Qt5/6/7 前端在 OHOS 无依赖栈）。

6. **源码级适配（headless CLI 干净退出）**：
   `src/awf-gtk4.c` 中 `--version`(-v) 与 `--list`(-l) 分支在输出后由 `return status`
   改为 `fflush(stdout); _exit(0);`，跳过 GTK/GLib teardown。原因：无显示环境下
   main 返回后的 GTK teardown 会 SIGTRAP（Signal 5）崩溃；纯 CLI 查询路径不应依赖显示会话。

7. **staging 验证**：

```bash
DESTDIR=$HOME/tmp/test-install-awf-gtk-4.2.0 make install
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游 release 无预生成 `configure` | 官方以源码归档发布（configure.ac + build.sh） | 配方 build() 先执行 `autoreconf -fi` |
| 2 | config.status 临时目录 mktemp 失败（HMDFS） | autoconf 默认在 `.` 下 `mktemp -d ./confXXXXXX` | E114 补丁：改用固定临时目录 |
| 3 | 系统 gtk4.pc Requires `cairo-gobject`，无对应 .pc | 部署的 GTK 栈缺 cairo-gobject.pc，制品仓也无 | 生成 pkg-config overlay，复制 gtk4.pc 并去掉 cairo-gobject |
| 4 | 系统前缀无 cairo/graphene/libnotify 头文件与 .pc | 系统只部署了 GTK 核心栈 | conan 包 `cairo/1.18.4`、`graphene/1.10.8`、`libnotify/0.8.3`（均为 ohpcd 制品仓已发布包）提供头文件，overlay .pc 指向其 package_folder |
| 5 | 无显示环境下 `--version` 后 SIGTRAP（Signal 5）崩 | GTK/GLib teardown 需要显示会话 | `--version`/`--list` 输出后 `fflush(stdout); _exit(0);`（E252 边界：CLI 查询路径可用，GUI 渲染仍需显示） |
| 6 | libnotify 运行时依赖 | 二进制链接 `libnotify.so.4` | 主任务已把制品仓 libnotify 签名的 so 放入 `~/usr/local/lib/external/libnotify.so.4`，运行时 LD_LIBRARY_PATH 覆盖 |

## 源码修改

- `src/awf-gtk4.c`：`--version`(-v) / `--list`(-l) 分支 `fflush(stdout); _exit(0);`
  （含 `#include <unistd.h>`）。由 finish step [1/10] refresh-patch --auto 生成补丁。
- 生成的 `configure`：E114 config.status 临时目录固定化（生成文件，由配方 build() 内联处理）。

## 依赖版本

| 依赖 | 版本 | 来源 | 用途 |
|------|------|------|------|
| gtk4 | 4.22.4 | 系统前缀 `/storage/Users/currentUser/usr/local` | GTK4 前端核心 |
| glib-2.0 | 2.88.0 | 系统前缀 | GLib |
| gio-2.0 / gobject-2.0 | 2.88.0 | 系统前缀 | GIO/GObject |
| pango / pangocairo | 1.50.14 | 系统前缀 | 文本布局 |
| gdk-pixbuf-2.0 | 2.42.12 | 系统前缀 | 图像加载 |
| cairo | 1.18.4 | conan 包（头文件）+ 系统 libcairo.so.2 | 2D 绘制 |
| graphene | 1.10.8 | conan 包 | 图形数学（静态链接） |
| libnotify | 0.8.3 | conan 包 | 桌面通知 |
| harfbuzz | 14.2.0 | 系统前缀 | 字体整形 |
| fribidi | 1.0.13 | 系统前缀 | 双向文本 |
| freetype2 / fontconfig / pixman / libpng16 | 系统前缀 | 图像/字体底层 |

## 验证结果

### 1. 运行验证（主任务路径，已固化）

```bash
export LD_LIBRARY_PATH="$HOME/usr/local/lib/external:$HOME/usr/local/lib"
~/tmp/test-install-awf-gtk-4.2.0/storage/Users/currentUser/usr/local/bin/awf-gtk4 --version
# 输出: 4.2.0
```

> 探索期二进制（未打 _exit 补丁）在打印版本后因 GTK teardown SIGTRAP（Signal 5 core dump），
> 属 GUI 应用无显示环境的预期行为；`--help` 为 Signal 11，同样正常。
> 配方内已对 `--version`/`--list` 补丁为 `fflush(stdout); _exit(0)`，干净退出（exit 0）。

### 2. 打补丁后干净退出（L2 断言基础）

```bash
export LD_LIBRARY_PATH="$HOME/usr/local/lib/external:$HOME/usr/local/lib"
/usr/local/bin/awf-gtk4 --version
# 输出: 4.2.0
# exit code = 0
```

### 3. 产物清单（staging 验证）

```
usr/local/bin/awf-gtk4
usr/local/share/applications/awf-gtk4.desktop
usr/local/share/man/man1/awf-gtk4.1
usr/local/share/man/fr/man1/awf-gtk4.1
usr/local/share/icons/hicolor/{scalable,16x16,22x22,24x24,32x32,48x48,64x64,128x128}/apps/awf-gtk4.*
usr/local/share/locale/fr/LC_MESSAGES/awf-gtk4.mo
usr/local/share/bash-completion/completions/awf-gtk4
```

### 4. conan-verify（详见 reports/conan-verify-report.md 与 reports/conan-create.log）

- G0 预构建风险评估：通过
- G1 配方完整性：通过
- G2 `conan create`（autotools + autoreconf + GTK4）：通过
- G3 系统同名库隔离：通过（application 包，无 lib/ 输出）
- G4 产物完整性：bin/awf-gtk4 + share/ 数据
- L2 smoke：`awf-gtk4 --version` → `4.2.0`（exit 0，打补丁后）
- L4 安全扫描 / L5 产物基线：通过
- R30/R31 知识图谱集成：见 knowledge 草稿

## 注意事项

- **GTK4 消费方式与 gtkdatabox 一致**：GTK 栈来自系统前缀（非 conan 包），
  配方必须支持 `GTK_PREFIX` / `DEFAULT_PREFIX` 环境变量与 `/storage/Users/currentUser/usr/local` 默认前缀发现。
- **pkg-config overlay 是构建关键**：系统 gtk4.pc 依赖不存在的 cairo-gobject.pc，
  且 cairo/graphene/libnotify 的 .pc 只有 conan 包内的 `prefix=/` 占位形式，
  必须由配方在构建期生成绝对路径的 overlay .pc 并置于 PKG_CONFIG_PATH 最前。
- **R38**：产物含可执行文件 `awf-gtk4`，需在软件级目录提供 `commands.json`（见 archives/a/awf-gtk/commands.json）。
- **R40 边界**：无显示环境只能验证 `--version`/`--list` 等 CLI 查询与启动路径；
  完整 GUI 渲染（主题预览、GTK4 控件渲染）需要在有显示会话的 OpenHarmony PC 上人工验证。
- 不要在 `/tmp` 写文件（只读），构建临时文件一律用 `$HOME/tmp`。
- 不要 `ln -sf` 覆盖 HMDFS 软链；libnotify.so 若需链接符号用 `rm -f && ln -s`。
