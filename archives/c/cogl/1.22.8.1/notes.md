# cogl 1.22.8.1 适配笔记（版本级）

> 本文件为版本级归档元数据（AI 元数据，CI 不读取）。上游测试清点与逐项
> 技术原因见 `test_package/notes.md`；本文件聚焦版本号策略、构建配置与
> 结论汇总。

## 1. 版本与来源

- 包版本：`cogl/1.22.8.1`
- 上游源码版本：`1.22.8`（GNOME Archive cogl tag 1.22.8，2020-06-04）
- 上游来源（R39 官方源）：
  `https://download.gnome.org/sources/cogl/1.22/cogl-1.22.8.tar.xz`
- 源码 sha256：`a805b2b019184710ff53d0496f9f0ce6dcca420c141a0f4f6fcc02131581d759`

**R37 版本递增说明（1.22.8 → 1.22.8.1）**：`1.22.8` 已在制品仓发布，
本轮修复必须递增后缀。修复内容 = 开启 `cogl-pango` 组件，补下游
Clutter 1.26.4 的硬依赖断链（详见下节）。

## 2. 本轮修复内容（R36 依赖断链补链）

- **根因**：Clutter 1.26.4 的 `configure.ac` 把 `cogl-pango-1.0` 写死在
  `CLUTTER_BASE_PC_FILES`，且**无任何 `--enable/--disable` 开关可关闭**
  （全文件检索确认）；而 `cogl/1.22.8` 的配方用 `--disable-cogl-pango`
  裁剪，包内不产出 `cogl-pango-1.0.pc`（实测 `p/lib/pkgconfig/` 仅
  `cogl-1.0.pc`/`cogl-path-1.0.pc`/`cogl-gles2-1.0.pc`），使下游
  `configure` 必然失败。
- **修复**：`--enable-cogl-pango`（产出 `libcogl-pango.so`、
  `cogl-pango-1.0.pc`、`cogl-pango.h`）；同时 `--enable-null-egl-platform`
  以安装公共头 `cogl/cogl-egl.h`（下游 EGL 后端需要）。
- **依赖选型**：新增 `pango/1.56.4`（`cogl-pango` 硬依赖仅 `pangocairo`）；
  `cairo/1.18.4` 作为 pango 传递依赖；`fontconfig/2.18.1.1` 以
  `force=True` 统一（cairo 钉 2.18.1 与 pango 要 2.18.1.1 冲突）。

## 3. 平台适配要点（OHOS）

1. **OHOS 无显示服务**：x11 / wayland / kms / xlib EGL 平台与
   gst / gdk-pixbuf 全部禁用；GL 驱动由制品仓 `gles2/2.0.25` +
   `egl/1.0.5` 提供（`--enable-gles2 --disable-gl`）。
2. **E236/E522（libtool 陈旧 `.la`）**：依赖包 `libxcb` 的 `.la` 其
   `dependency_libs` 指向已清理的构建机临时目录（`libXau.la`），libtool
   递归读取报 `not a valid libtool archive`。配方 `generate()` 内建
   `deps-nola` 私有目录（只放依赖 `.so` 符号链接、无 `.la`）并置于
   `extra_ldflags` 最前解决；**未修改 Conan 依赖缓存**。
3. **静态 libEGL.a 的 C++ 符号**：制品仓 `egl/1.0.5` 为静态 `libEGL.a`
   （Khronos EGL 的 OHOS 后端是 C++）。在生成的 `egl.pc` 的 `Libs` 中
   **紧跟 `-lEGL`** 追加 `-lc++_shared`（顺序关键），否则 `libcogl.so`
   残留未解析 `std::__n1::mutex` 符号，消费者加载 rc=127。
4. **`eglmesaext.h` 平台头缺口**：cogl 公共头 `cogl-egl-defines.h` 在
   `COGL_HAS_EGL_SUPPORT` 下 `#include <EGL/eglmesaext.h>`（Mesa 专有头，
   OHOS SDK 全检索为空）。cogl 源码零处使用任何 `EGL_MESA_*` 符号，故
   生成最小 stub 并**随包双路径安装**（`include/EGL/` 与
   `include/cogl/EGL/`——后者因 cogl 自带 `cogl-1.0.pc` 的 Cflags 为
   `-I${includedir}/cogl`）。
5. **E011/E129（HMDFS 上 `umask 077` 不可写）**：`configure` 的 confstat
   用 `umask 077 && mktemp -d` 建临时目录，HMDFS 强制 setgid 得
   `drwx--S---`，连属主不可写；配方内改 `umask 022`。

> 本配方**未引入任何 `__OHOS__` 平台宏**（无源码 patch 文件），平台适配
> 全部经 configure 开关裁剪与配方内等价修正完成。

## 4. 测试与验证结论（R51 三步法）

- **上游测试清点**：72 例（conform 注册 52 + 未移植 12 + unit 白盒 7 +
  micro-perf 1），逐项取自 `test_package/notes.md`。
- **可运行环境实跑**：纯 CPU 子集 **3/3 通过**（`test_color_hsl` /
  `test_no_gl_header` / `test_version`，源文件零改动）；其余 69 例需 GL
  渲染环境——OHOS 无 `/dev/dri`，实测 `cogl_context_new(NULL)` 直接
  SIGSEGV，**如实记录为「0 运行（非失败）」**。
- **test_package 消费者验证**：**9/9 PASS**（5 项安装布局与 cogl-pango
  组件检查 + 1 项 consumer 真实编译链接运行 + 3 项上游纯 CPU 用例实跑）。
- **conan create**：`EXIT=0`，W3 本地 CI 全门禁通过
  （`L0_RESULT=pass` / `L1_RESULT=pass` / `L1e` 破坏性反向验证通过）。

## 5. 已知限制

- cogl 属图形/GL 底层库（R40 深度适配类）。本包证明「可编译、可链接、
  可加载、纯 CPU API 可实跑」，**渲染路径的端到端验证需在具备显示能力
  与 GPU 节点的设备上补足**。
- 需 GL 的 69 例上游测试在本环境不可运行，非本包缺陷。

---

**编译结束**: 2026-09-29
**最终状态**: built
