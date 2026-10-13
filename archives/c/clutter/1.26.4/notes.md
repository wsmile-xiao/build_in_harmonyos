# clutter 1.26.4 适配笔记（本地实测）

## 编译环境
- 构建系统: autotools（tarball 自带 `configure`/`Makefile.in`，无需 autoreconf）
- 编译日期: 2026-09-29
- 编译器: clang 15 / libc++（OHOS aarch64 原生，非交叉）
- 状态: built（`conan create` EXIT=0，test_package ALL PASS）
- 包引用: `clutter/1.26.4@ohpcd/stable`

## 目标版本核实（重要）

分支名为 `feat/clutter-1.27.4`，但**上游不存在 1.27 系列**。逐项核实：

| 核实手段 | 结果 |
|---|---|
| GNOME 官方 `download.gnome.org/sources/clutter/cache.json` | 最高 `1.26.4`，`1.27` 出现 0 次 |
| GNOME 官方 `1.27/`、`1.28/` 目录 | 均 HTTP 404 |
| GNOME Archive/clutter GitLab tags（全分页） | 最高稳定 tag `1.26.4`（2020-03-09） |
| 上游 master 的 `configure.ac` / `meson.build` | `1.26.5`（奇数微号=开发中，**无正式发布**） |
| Debian/Alpine/Fedora/openSUSE/openmandriva/Guix/openEuler | 最高均 `1.26.4` |
| 仓库 `search-url` 给出的 `www.clutter.org/clutter-1.27.4.tar.gz` | **假阳性**：随机文件名同样 302→200（停靠/域名出售页）；`clutter.org` 无源码分发能力；savannah 路径实测 404 |

经用户确认，改按真实上游最新稳定版 **1.26.4** 适配，并将分支重命名为
`feat/clutter-1.26.4`（旧 `feat/clutter-1.27.4` → 新 `feat/clutter-1.26.4`）。

源码与官方校验文件逐字节一致：
`clutter-1.26.4.tar.xz` sha256 = `8b48fac159843f556d0a6be3dbfc6b083fc6d9c58a20a49a6b4919ab4263c4e6`
（与官方 `clutter-1.26.4.sha256sum` 一致）。

## 编译步骤

1. `conan create . -pr:h=~/.conan2/profiles/ohos -pr:b=~/.conan2/profiles/ohos --build=missing --user=ohpcd --channel=stable`
2. 配方 `generate()`：PkgConfigDeps + AutotoolsToolchain；并建 `deps-nola`
   私有目录（E236/E522，见下）。
3. `build()`：E011 umask 修正 → 组装 PKG_CONFIG_PATH/LD_LIBRARY_PATH →
   注入 GLib 代码生成工具 → `./configure`（只启用 EGL 后端）→ 从顶层
   Makefile 摘除 `tests`/`doc`/`po`/`examples` → `make -j1` → `make install`。
4. `package()`：删除 `.la`（libtool 归档含构建机绝对路径，不可分发）。
5. test_package：`test_clutter.py` 编译并**实跑** `consumer.c`。

## 上游测试清点与实跑（R51 三步法）

### 第 1 步：清点（逐文件实测，非估算）

| 目录 | 构建方式 | 用例数 |
|------|----------|--------|
| tests/conform | glib-tap.mk 注册 TESTS（26 个 test_programs + 15 个 script-*.json） | 41 |
| tests/interactive | check_PROGRAMS（交互式演示） | 53 |
| tests/accessibility | check_PROGRAMS（cally-*-example） | 5 |
| tests/micro-bench | check_PROGRAMS | 5 |
| tests/performance | check_PROGRAMS | 7 |
| **合计** | | **111** |

（conform 的 26 个程序 = actor_tests 13 + general_tests 7 + classes_tests 1
+ deprecated_tests 5，逐项取自 `tests/conform/Makefile.am`。）

### 第 2 步：可运行环境实际运行

**实测结论：111 项全部不可运行（0 运行）**，技术原因逐项如下：

1. **所有测试程序都需要 Clutter 后端**：任何 conform/interactive 用例入口
   都经 `clutter_init()` 建立窗口系统后端 + EGL/GL 渲染上下文。OHOS 本
   环境**无显示服务**（无 X11/Wayland/DRM），本配方只启用 EGL 后端，
   无可用 display/device 时无法建立上下文。
2. **无 GPU 节点**：同栈的 cogl/1.22.8 实测 `cogl_context_new(NULL)` 在
   本机直接 SIGSEGV（见 `archives/c/cogl/1.22.8/test_package/notes.md`），
   底层 GL 上下文本身无法创建。
3. **interactive 类为交互式程序**：即使有后端也需人工输入，`make check`
   会挂死（故本配方不把 tests 纳入构建期，避免 CI 超时）。

> 如实记录为「0 运行、非失败」，未冒充通过；这与 `cogl/1.22.8` 的处理
> 口径一致（该包 72 例中仅 3 例纯 CPU 可跑，其余 69 例同样因无 GL 环境
> 省略）。

### 第 3 步：消费者视角可运行子集（test_package 实跑）

上游无「免显示」的独立测试程序，故补 **鸿蒙可运行子集**：`consumer.c`
实质调用 Clutter 中不依赖显示上下文的真实 API，并由 `test_clutter.py`
编译 + 运行：

| # | 断言 | 覆盖的库内代码路径 |
|---|------|-------------------|
| 1–3 | 版本宏 1.26 / `CLUTTER_CHECK_VERSION(1,26,0)` 真 / `(1,27,0)` 假 | 版本契约 |
| 4–7 | `clutter_color_from_string("#7f7f7f")` + 分量校验 + `to_hls` 灰度色 hue/lum/sat | 颜色解析与色彩空间换算 |
| 8 | `clutter_units_from_pixels`/`to_pixels` 往返 == 42 | 单位换算（经 ClutterSettings 单例） |
| 9–12 | `clutter_actor_new` 非空 + `set/get_size` 往返 320x240 + 名称属性往返 | Actor 对象生命周期与属性系统 |
| 13–14 | reactive 默认 FALSE（与上游 `g_param_spec_boolean(..., FALSE, ...)` 契约一致）+ `set_reactive(TRUE)` 后可读为真 | GObject 属性默认值与可写性 |
| (+1) | `g_object_unref` 无崩溃（打印型检查，不计入断言数） | 析构路径 |

实测结果：`SUMMARY: 14/14 checks passed` —— 即 14 项 CHECK 断言全部通过；
另有 3 项前置检查（`libclutter-1.0.so`/`clutter.h`/`clutter-1.0.pc` 存在性）
亦全部 PASS，终态 `ALL PASS`。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 目标版本 1.27.4 上游不存在 | 分支名与实际上游不符 | 核实后按 1.26.4 适配并重命名分支（已记录旧/新名） |
| 2 | configure 报缺 `cogl-pango-1.0` | clutter 硬依赖该 .pc 且无开关可关；制品仓 cogl/1.22.8 用 `--disable-cogl-pango` 裁剪 | 先在 cogl 侧补链（新发 `cogl/1.22.8.1`，`--enable-cogl-pango`） |
| 3 | configure 报 `No package 'cairo-gobject' found` | cairo/1.18.4 配方 `glib=disabled`，不产 cairo-gobject.pc | 改用 `cairo/1.18.4.1`（glib=enabled），并用 `force=True` 压制 pango 的精确 pin |
| 4 | 图解析报 `Version conflict: fontconfig/2.18.1 vs 2.18.1.1` | cairo 钉 2.18.1，pango 要 2.18.1.1 | 统一 `fontconfig/2.18.1.1`（`force=True`） |
| 5 | 链接报 `libXau.la ... is not a valid libtool archive` | 依赖包 libxcb 的 `.la` 其 `dependency_libs` 指向已清理的构建机临时目录 | **E236/E522**：配方 `generate()` 建 `deps-nola` 私有目录（只放依赖 `.so` 符号链接、无 `.la`）并置于 `extra_ldflags` 最前 |
| 6 | cogl 编译 `cogl-egl-defines.h` 报缺 `EGL/eglmesaext.h` | 该头为 Mesa 专有，OHOS SDK 无（已验证）；cogl 公共头硬包含 | 在 cogl/1.22.8.1 内生成最小 stub 并随包装到 `include/EGL/` 与 `include/cogl/EGL/`（cogl 源码零处使用 `EGL_MESA_*`） |
| 7 | cogl 启用 EGL 后链接缺 `std::__n1::mutex` 等 C++ 符号 | 制品仓 egl/1.0.5 为**静态** `libEGL.a`（C++ 实现） | 在 cogl 配方的 `egl.pc` 的 `Libs` 中紧跟 `-lEGL` 追加 `-lc++_shared`（顺序关键；且须改 `.pc` 而非 configure 变量，因 `-lEGL` 实际来自该 `.pc`） |
| 8 | 消费者加载 `libclutter-1.0.so` 报 `libjson-glib-1.0.so.0: needed by ...` + 全部 `json_*` 重定位失败（rc=127） | `json-glib/1.10.6` 的 `.so` 其 `.codesign` 段被 OHOS 加载器判无效：`dlopen` 报 **Permission denied**（`chmod 755` 无效，重新 `selfSign` 后 OK；实测对照见下） | 改用本仓重签版 `json-glib/1.10.6.1`（实测 `dlopen` OK） |
| 9 | test_package 找不到 `cogl/cogl.h`、`json_*` 符号 | 手工 `-I/-L` 拼接与真实消费者路径不一致 | `test_clutter.py` 优先走 `pkg-config`（真实消费者标准路径，并顺带验证安装出的 `.pc` 的 Requires 链），不可用时回退拼接 |

### 问题 8 的实测对照（决定性证据）

| 操作 | `dlopen` 结果 |
|------|---------------|
| `json-glib/1.10.6` 原样 `.so` | ❌ `Permission denied` |
| 复制副本 + `chmod 755`（不重签） | ❌ `Permission denied` |
| 复制副本 + 删除 `.codesign` + `binary-sign-tool selfSign` | ✅ OK |
| `json-glib/1.10.6.1`（本仓重签版） | ✅ OK |

同批对照中，clutter 的其余 31 个 `NEEDED` 依赖全部 `dlopen` OK，仅
`libjson-glib` 一项异常 —— 故定位为该包单独的签名问题，而非本配方缺陷。

## 平台限制说明（如实记录）

- **无显示服务 / 无 `/dev/dri`**：Clutter 作为图形 UI 框架（R40 深度适配
  类），其运行时能力（stage/actor 渲染、事件分发）在 OHOS 本环境无法建立
  后端，因此上游 111 项测试全部不可运行。本配方交付的是**可编译、可链接、
  可加载、免显示 API 可实跑**的库产物；渲染路径的端到端验证需在有显示
  能力的设备上另行进行。
- 本配方未引入任何 `__OHOS__` 平台宏（PF5 合规），平台适配全部经
  configure 开关裁剪与配方内等价修正完成。

## 依赖版本

```
cogl/1.22.8.1   glib/2.84.0.1   cairo/1.18.4.1   pango/1.56.4
atk/2.38.0.1.1  json-glib/1.10.6.1                fontconfig/2.18.1.1
gles2/2.0.25    egl/1.0.5
```
---

**编译结束**: 2026-10-10 21:52
**最终状态**: built
