# robtk 0.8.6 适配笔记（HarmonyOS / OpenHarmony aarch64）

## 1. 概要

| 项 | 值 |
|----|----|
| 软件 / 版本 | robtk / 0.8.6（上游 tag `v0.8.6`） |
| 上游地址 | https://github.com/x42/robtk |
| 源码 | `https://github.com/x42/robtk/archive/refs/tags/v0.8.6.tar.gz` |
| SHA256 | `ac68271db9605d83855460794b13826360841bff8aa76bb011c15454c56008a8` |
| License | GPL-2.0-or-later |
| 包类型 | `header-library`（源码工具箱：只交付头文件 + 源码，由消费者编译） |
| 构建系统（上游） | **无**（只有 `robtk.mk` 供下游插件 make 包含） |
| 编译日期 | 2026-09-26 |
| 编译器 | clang 15.0.4 / OHOS SDK 26.0.0.18（`--target=aarch64-linux-ohos`） |
| 状态 | built（本地 W3 `conan create` 通过；CI 合入后发布） |

robtk 不是一个可编译成 `.a/.so` 的库：它是 **LV2 插件 UI 工具箱**，下游插件项目用
`RW=<robtk 目录>` + `#include "robtk.h"` + `$(RW)ui_gl.c` 的方式把工具箱源码编进自己的 UI
共享对象。因此本包的交付形态是「头文件 + 源码 + 上游 robtk.mk」，`conanfile.py` 不做编译，
只做补丁应用与打包。

## 2. 上游测试入口清点（R51 三步法第 1 步，真实命令）

```bash
$ cd /storage/Users/currentUser/tmp/builds/robtk-0.8.6.orig
$ ls -a
. .. .tarball-sha256 AUTHORS COPYING README.md gl gpg_check.c gpg_init.c gpg_lv2ext.c gtk2 \
jackwrap.c jackwrap.mm lv2_rgext.h lv2syms lv2uisyms pugl robtk.h robtk.mk robtkapp.c rtk \
sofd ui_gl.c ui_gtk.c weakjack widgets win_icon.rc

$ find . -maxdepth 2 \( -name "Makefile*" -o -name "CMakeLists.txt" -o -name "configure*" \
    -o -name "meson.build" -o -name "*.pro" -o -name "Cargo.toml" \)
（输出为空 → 无任何构建系统入口）

$ find . -maxdepth 2 -type d \( -name "test*" -o -name "check" \)
（输出为空 → 无测试目录）

$ find . -type f | wc -l   # 51（原始 tarball 全量清单，实测于 /storage/Users/currentUser/tmp/robtk-pristine）
$ find . -name "*.c" | wc -l   # 11
$ find . -name "*.h" | wc -l   # 29
$ find . -maxdepth 2 \( -name "Makefile*" -o -name "CMakeLists.txt" -o -name "configure*" -o -name "meson.build" \) | wc -l   # 0
$ find . -maxdepth 2 -type d -name "test*" | wc -l   # 0
```

**结论：上游 0.8.6 既没有构建系统，也没有任何自动化测试入口**（无 tests/、无 ctest/pytest
注册、无 check 目标、无 CI 配置）。本包不删除也不修改任何上游测试；`test_package` 不能替代
上游测试统计，本包的上游测试统计为 **0 项（无入口）**，全部 60 项断言均来自本次新增的
消费者测试与鸿蒙特有测试（见 §6）。

## 3. OHOS 适配设计

### 3.1 平台缺口

上游 0.8.6 的 UI 呈现层只有两条路：

| 后端 | 依赖 | 在 HarmonyOS 上 |
|------|------|-----------------|
| `ui_gl.c` + `pugl/pugl_x11.c` | X11/GLX + 桌面 OpenGL 固定管线 | ❌ 无 X server / 无 GLX / 无桌面 GL（只有 EGL + OpenGL ES） |
| `ui_gtk.c` + `gtk2/` | GTK+ 2 | ❌ 上游自 0.8.6 起标注 deprecated，且 GTK2 不在制品仓 |

关键观察：**工具箱的组件与布局内核是平台无关的**——`rtk/common.h`（cairo 绘制/配色）、
`gl/layout.h`（容器与布局，1096 行）、`widgets/*.h`（15 个组件）全部只用 cairo + pango，
不依赖 GL/X11；真正与平台耦合的只有 `ui_gl.c` 这个「宿主驱动」以及它用到的 pugl 窗口后端。
GL 调用在 `ui_gl.c` 里仅集中在 3 个呈现函数（`opengl_init` / `opengl_reallocate_texture` /
`opengl_draw`）。

因此适配 = **给 pugl 增加 HarmonyOS 后端（EGL + OpenGL ES 3 + OHNativeWindow）**
+ **把 ui_gl.c 的呈现层换成 OpenGL ES**，组件/布局层零改动。

### 3.2 新增后端能力（pugl/pugl_ohos.c，762 行）

- EGL 1.4 初始化、`EGL_OPENGL_ES3_BIT` 配置选择（失败回退 ES2）、ES3/ES2 上下文创建；
- 两种呈现目标（由 `puglCreate()` 的 `parent` 参数选择）：
  - `parent != 0`：宿主 ArkUI/XComponent 提供的 `OHNativeWindow*` → `eglCreateWindowSurface`
    + `eglSwapBuffers` 上屏，并用 `OH_NativeWindow_NativeWindowHandleOpt(SET_BUFFER_GEOMETRY)`
    同步缓冲尺寸；
  - `parent == 0`：EGL pbuffer **离屏渲染** → 无窗口也能构建、驱动、校验 UI（CI 无显示器可用）；
- 输入桥接（HarmonyOS 由应用持有事件循环，pugl 无法 poll 服务端，因此由宿主推入）：
  `puglSendMotion/Mouse/Scroll/Special/Keyboard/EnterLeave/Close` 入队，
  `puglProcessEvents()` 出队派发到既有回调；`puglSetNativeWindow()` 支持运行期挂接/摘除窗口；
- 帧回读 `puglGrabFrame()`（glReadPixels）——供宿主快照与自动化像素校验；
- 隐藏时不再渲染（`puglHideWindow` 语义化：ArkUI 表面隐藏期间停止绘制）。

### 3.3 呈现层替换（gl/gles_present.h，209 行）

HarmonyOS 只有 OpenGL ES 3.x，`ui_gl.c` 的固定管线（`glMatrixMode/glOrtho/glBegin/
glTexEnvi/GL_TEXTURE_RECTANGLE_ARB`）不可用。替换为一个极小的 blit 程序：

- cairo `ARGB32`（小端上即预乘 BGRA）上传为 `GL_RGBA` 纹理，**在片元着色器里用 `.bgra`
  swizzle 还原字节序**——不依赖 `GL_EXT_texture_format_BGRA8888`；
- 全屏 quad（NDC）+ `GL_CLAMP_TO_EDGE`（NPOT 安全），预乘 alpha 对应
  `glBlendFunc(GL_ONE, GL_ONE_MINUS_SRC_ALPHA)`；
- **blit program 按 EGL 上下文缓存**：GL program 名是 per-context 的，UI 实例销毁后重建会拿到
  新上下文（见 §5 #11），因此 `opengl_init()/opengl_draw()` 用 `eglGetCurrentContext()` 判定
  上下文是否变化，变化即重建程序，避免用到已失效的 program 名；
- `ui_gl.c` 中另 3 处矩阵调用（reshape 路径）在 `RTK_GLES` 下省略，投影由 quad 自身承担。

### 3.4 宿主接口（gl/ohosui.h，53 行）

桌面环境下窗口管理器负责投递事件；HarmonyOS 上应用持有窗口，必须能拿到视图并转发事件。
为此通过标准 LV2 `extension_data()` 暴露一个可选扩展接口：

```c
#define RTK_OHOS_UI_URI "http://gareus.org/oss/lv2/robtk#ohosUi"
typedef struct {
    uint32_t   abi_version;   /* = 1 */
    PuglView*  (*view)(LV2UI_Handle);
    int        (*grab_frame)(LV2UI_Handle, int*, int*, unsigned char*);
} RTKOhosUi;
```

宿主拿到 `PuglView*` 后即可调用 §3.2 的 pugl 扩展（挂窗口 / 转发输入 / 回读帧）；不需要它的
宿主忽略即可，接口是附加式的。

### 3.5 补丁清单（patches/，由 `ohc-run.py refresh-patch --auto` 生成）

| 补丁 | 内容 |
|------|------|
| 0001-gl-gles_present.h.patch | 新增 OpenGL ES 呈现层（209 行） |
| 0002-gl-ohosui.h.patch | 新增 HarmonyOS 宿主接口定义（53 行） |
| 0003-pugl-pugl_internal.h.patch | `PUGL_GLES_BACKEND` 下跳过固定管线默认 reshape（+6/-1） |
| 0004-pugl-pugl_ohos.c.patch | 新增 HarmonyOS pugl 后端（762 行，含几何钳制与离屏退化尺寸保护） |
| 0005-pugl-pugl_ohos.h.patch | 新增后端扩展 API 声明（86 行） |
| 0006-robtk.mk.patch | `RTK_OHOS=1` 时选 `pugl_ohos.c`、加 `-DRTK_GLES`、链 `-lEGL -lGLESv3 -lnative_window`（+10） |
| 0007-rtk-common.h.patch | `get_text_geometry()` 约束文本度量（`RTK_TEXT_MEASURE_MAX` 4096，负值归 0）：宿主字体栈损坏时 pango 会返回数十万像素的垃圾度量，不能让它污染组件布局/可绘制尺寸/画布分配（+15） |
| 0008-ui_gl.c.patch | GLES 头文件/呈现函数分支、reshape 投影分支、离屏模式允许无父窗口（+50/-5） |

补丁新增行中不含 `__OHOS__` 平台宏（PF5 口径）：平台选择走 `RTK_GLES`（由包 `cpp_info.defines`
与 `robtk.mk` 显式给出），属于「后端显式选择」而非「平台宏兜底」，逻辑实质、无空壳。

## 4. 真实构建（证据）

### 4.1 手工交叉编译（开发阶段，设备上真实编译器）

```bash
$ clang --target=aarch64-linux-ohos --sysroot=$SDK/sysroot -O1 -g -fPIC \
    -DRTK_GLES -DRTK_OFFSCREEN -DHAVE_IDLE_IFACE -DHAVE_LV2_1_18_6 \
    -DRTK_URI='"http://example.org/robtk#test"' -DRTK_GUI='"robtk-test"' \
    -DPLUGIN_SOURCE='"plugin_test.c"' \
    ui_gl.c pugl/pugl_ohos.c test_robtk_ui.c \
    -o test_robtk_ui $(pkg-config --cflags --libs cairo pango pangocairo lv2) \
    -lEGL -lGLESv3 -lnative_window -lm -lpthread -ldl
# 退出码 0，产物 186880 字节
```

### 4.2 `conan create`（W3 同源验证）

```bash
$ conan create archives/r/robtk/0.8.6 \
    -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=robtk/*
# 退出码 0
# 日志: archives/r/robtk/0.8.6/reports/conan-create.log（W3 由 finish 重新生成并在 .ci-result.json 中记录 SHA256）
```

产物内容（`package(): Packaged ...` 原文）：

```
32 '.h' files, 12 '.c' files, 2 '.mm' files, 1 '.mk' file, 1 '.cpp' file, 1 '.md', COPYING
→ <pkg>/include/robtk/...（rw=RW 用法）、<pkg>/licenses/COPYING
```

## 5. 遇到的问题 → 根因 → 修复

| # | 现象（首个错误行） | 根因 | 修复 |
|---|-------------------|------|------|
| 1 | `ld.lld: error: undefined symbol: OH_NativeWindow_NativeWindowHandleOpt` | 系统 `libnative_window.so` 未链接 | 链接加 `-lnative_window`（同时写入 `robtk.mk` 与 `cpp_info.system_libs`） |
| 2 | `ld.lld: error: undefined symbol: ui_enable` / `ui_disable` | 这两个符号按上游约定由**插件侧**（PLUGIN_SOURCE）提供 | 测试 UI 中实现（进入/离开屏幕时开关 port_event 处理），非空壳 |
| 3 | `pugl_internal.h:100: undefined symbol: glOrtho` | 只给了 `-DRTK_GLES`，pugl 平台无关部分仍在用固定管线 | OHOS 后端自身 `#define PUGL_GLES_BACKEND 1`（后端自带约束，调用方无需再传） |
| 4 | ASan `heap-buffer-overflow` @ `rtk_test_ui_*` | `LV2UI_Handle` 是工具箱的 `GLrobtkLV2UI*`，不是插件的 UI 结构体；测试辅助函数误转型 | 改为经 `puglGetHandle(view)` 取 `self->ui`（测试辅助函数签名收 `PuglView*`） |
| 5 | `eglInitialize` 成功但 `glGetString(GL_VERSION)` 返回 NULL、着色器编译失败 | 链接 `-lGLESv2` 解析到的是 NDK 桩（`/system/lib64/ndk/`），非真实驱动 | 改链 `-lGLESv3`（真实驱动，实测 `Maleoon 916 / OpenGL ES 3.2 B301`） |
| 6 | 离屏首帧全黑、无渲染 | `puglCreate` 后 `view->resize/redisplay` 均为 false（X11 靠 `MapNotify`/`Expose` 触发） | 后端在 create 时就请求一次 reshape + redisplay |
| 7 | `pango` 报 `Fontconfig error: Cannot load default config file` | 无 `FONTCONFIG_PATH`（工程内无系统 fonts.conf） | 本机在该状态下仍能找到字体族（240 族），但 **CI worker 完全相同报错下字体度量退化为垃圾值** —— 见 #12；测试已改为不依赖字体（仅 dial） |
| 8 | `ERROR: Package type is 'library', but no 'shared' option declared` | conan 对 `library` 强制要求 `shared` 选项，而本包无二进制产物 | `package_type = "header-library"`（语义：无编译产物，仅头/源码） |
| 9 | `package(): WARN: No files in this package!` | `conan.tools.files.copy(dst=...)` 的 `dst` **不会**自动拼 `package_folder`，相对路径落到了构建目录 | `dst=os.path.join(self.package_folder, ...)` |
| 10 | `'lv2/lv2plug.in/ns/extensions/ui/ui.h' file not found` | 制品仓 `lv2/1.18.11-git` 只有新布局 `lv2/ui/ui.h`；测试 TU 未定义 `HAVE_LV2_1_18_6` | 用 INTERFACE 目标（`robtk_test_config`）把 `HAVE_LV2_1_18_6` 等定义统一传播给所有 TU |
| 12 | **CI 平台报错**：`pugl: eglCreatePbufferSurface failed (EGL error 0x3004)` → `FAIL instantiate() built the widget tree`（本地/首轮均通过） | CI worker 的字体栈不可用（日志：`Fontconfig error: Cannot load default config file`）。此时 **pango 的文本度量退化为垃圾值**（本机复现：11px 字号返回 477806 / 1289667 / 1704629 px，每次不同），robtk 的 label 用文本度量算尺寸 → vbox → 宿主 `self->width/height` 变成数十万像素 → EGL 以 `EGL_BAD_ATTRIBUTE`（0x3004）拒绝该 pbuffer 尺寸 → `instantiate()` 失败 | 三层修复：①`rtk/common.h` 的 `get_text_geometry()` 约束文本度量（负值归 0、上限 `RTK_TEXT_MEASURE_MAX=4096`），垃圾度量不再传播；②`pugl_ohos.c` 对 pbuffer/窗口尺寸做合法性钳制（含 `EGL_MAX_PBUFFER_WIDTH/HEIGHT` 查询）并打印请求尺寸，`puglResize` 保证 `view->width/height ≥ 1`；③测试 UI 不再依赖字体（仅用 dial，几何固定 55x30），并新增"退化尺寸仍可创建 drawable"回归断言。复现验证：模拟 CI 字体环境连跑 10 次 31/31 全通过（修复前该类环境会随机失败/崩溃） |
| 11 | 第 2 个 UI 实例渲染后 `glReadPixels` 报 `GL_INVALID_VALUE`（0x0501），帧取不到（0x0）——由新增的生命周期断言发现 | `gl/gles_present.h` 把 blit program 名缓存在文件级 static，但 **GL program 名是 per-EGL-context 的**：`puglDestroy()` 里 `eglTerminate` 之后新建实例拿到新上下文，旧 program 名已失效，`glUseProgram()` 产生 `GL_INVALID_VALUE`、绘制静默失败 | 用 `eglGetCurrentContext()` 记录 program 所属上下文，`opengl_init()/opengl_draw()` 在上下文变化时重建程序；`puglGrabFrame()` 读回前清空历史 GL 错误，使报错只反映 `glReadPixels` 本身 |

## 6. 测试与结果（逐项）

测试运行环境：真机 HarmonyOS（HongMeng Kernel 1.12.0 aarch64，HUAWEI Maleoon 916 GPU，
EGL 1.4 / OpenGL ES 3.2），`conan create` 的 test_package 阶段真实执行（非交叉跳过）。

### 6.1 上游测试

无入口（§2），0 项，未运行、未修改。

### 6.2 本次新增测试 A：`test_pugl_ohos`（鸿蒙特有，后端层）

命令：`./test_pugl_ohos` ｜ 结果：**29 检查，0 失败，退出码 0**

| # | 用例 | 结果 |
|---|------|------|
| 1 | puglCreate() 建立离屏 EGL/GLES 视图 | ✅ |
| 2 | 离屏视图无原生窗口句柄 | ✅ |
| 3 | puglProcessEvents() 正常返回 | ✅ |
| 4 | 首帧 reshape 触发 1 次 | ✅ |
| 5 | 首帧 display 触发 1 次 | ✅ |
| 6 | OpenGL ES 上下文可用（`OpenGL ES 3.2 B301`） | ✅ |
| 7 | 首帧后无 GL 错误 | ✅ |
| 8 | puglGrabFrame() 成功 | ✅ |
| 9 | 帧尺寸 64x48 | ✅ |
| 10 | 帧内容 = 64,128,191（与 glClearColor 一致） | ✅ |
| 11 | 输入事件入队、processEvents 前不派发 | ✅ |
| 12 | motion 事件派发（3 次，含 leave 的 -1,-1） | ✅ |
| 13 | motion 坐标正确（11,22） | ✅ |
| 14 | 按键按下/抬起派发（2 次 / 1 次 press） | ✅ |
| 15 | 滚轮派发（1 次） | ✅ |
| 16 | 特殊键派发（2 次） | ✅ |
| 17 | 焦点进入/离开派发（2 次） | ✅ |
| 18 | 修饰键状态跟踪（PUGL_MOD_CTRL=0x2） | ✅ |
| 19 | puglPostRedisplay() 触发一次重绘 | ✅ |
| 20 | puglPostResize() 重建 drawable（reshape +1） | ✅ |
| 21 | 隐藏时不再渲染 | ✅ |
| 22 | puglShowWindow() 恢复渲染 | ✅ |
| 23 | puglSetNativeWindow(0) 摘除窗口句柄 | ✅ |
| 24 | 视图存活期间 EGL 上下文为 current | ✅ |
| 25 | puglDestroy() 释放 EGL 上下文（`eglGetCurrentContext()` 归零） | ✅ |
| 26 | 退化尺寸（-1x-1）仍能创建离屏 drawable（钳制生效，不触发 EGL_BAD_ATTRIBUTE） | ✅ |
| 27 | 钳制后的 drawable 完成 reshape + display | ✅ |
| 28 | 钳制后的 drawable 可回读帧（1x1） | ✅ |
| 29 | （同 13 的坐标复核：33,44 与 CTRL 修饰） | ✅ |

### 6.3 本次新增测试 B：`test_robtk_ui`（全栈，消费者视角）

命令：`./test_robtk_ui` ｜ 结果：**31 检查，0 失败，退出码 0**

覆盖：`lv2ui_descriptor(0)` 入口与 URI、`instantiate()` 构建组件树、离屏无窗口句柄、
`RTK_OHOS_UI_URI` 扩展接口（ABI=1 / view / grab_frame）、idle 接口、帧回读（固定 55x30）、
主题背景渲染、字体无关的 dial 渐变像素校验（≥8 种颜色）、组件布局
（dial 55x30）、指针拖拽 → 8 次数值上报控制端口 0、值域 [0,100] 校验、拖拽后帧变化
（900 字节）、滚轮再次上报、**指针离开不产生额外控制端口写入**、resize 后仍渲染、hide/show
后仍渲染、**cleanup() 后可再次实例化第二个 UI 并独立渲染出帧**（该生命周期断言即发现 §5 #11 的
per-context program 缺陷）。

统计：**总 60 项断言（29 + 31），通过 60，失败 0，跳过 0**。
日志路径：`archives/r/robtk/0.8.6/reports/conan-create.log`（conan create 汇总 W3 阶段）与
`reports/w3-local-ci.log`；开发期单独日志见 `/storage/Users/currentUser/tmp/robtk-dev/`。

## 7. 鸿蒙特有测试说明（新增）

`test_package/test_pugl_ohos.c` 是针对**本次新增的 HarmonyOS 平台层**的专项测试：它不使用任何
宏开关去「假装」桌面行为，而是直接调用 HarmonyOS 图形栈（EGL + OpenGL ES 3 + EGL pbuffer），
验证（a）ES 上下文与 drawable 的真实可用性、（b）ArkUI 输入桥接的完整事件语义、
（c）帧回读像素与 `glClearColor` 逐字节一致、（d）resize 时 drawable 重建、（e）隐藏期不渲染。
`test_robtk_ui.c` 则在同一平台层之上跑通整条 UI 链路（LV2 入口 → 组件树 → cairo/pango →
GLES 呈现 → 输入 → 数值回传宿主）。

## 8. 依赖版本

| 依赖 | 版本 | 说明 |
|------|------|------|
| cairo | 1.18.4 | 组件绘制（pkg-config 名 `cairo`） |
| pango | 1.50.14.1.1 | 文本布局（`pango` / `pangocairo`） |
| lv2 | 1.18.11-git | LV2 UI/atom/urid/options 头文件（新布局，`HAVE_LV2_1_18_6`） |
| glib（传递） | 2.84.0.1 | 经 pango 传递 |

系统库（OHOS）：`EGL`、`GLESv3`、`native_window`、`m`、`pthread`。

## 9. 已知限制与注意事项

1. **X11/GLX 后端在 HarmonyOS 上不可用**：下游必须用 `RTK_OHOS=1`（make）或
   `-DRTK_GLES`（其他构建系统）编译 UI；包的 `cpp_info` 在 OHOS 上已默认给出 `RTK_GLES`。
2. **上屏模式需要宿主提供 `OHNativeWindow`**（ArkUI XComponent），并通过 `puglSetNativeWindow()`
   挂接；未提供时自动走离屏 pbuffer（CI/测试路径）。
3. **EGL 上下文单线程约定**：视图创建后上下文保持 current，宿主应在同一线程调用
   `puglProcessEvents()`（对应 robtk 的 `HAVE_IDLE_IFACE` 模式）。
4. **文件选择对话框**：`puglOpenFileDialog()` 在 HarmonyOS 上由 ArkUI 侧实现（返回 -1，
   宿主通过 view 的 file-selected 回调回填），因此 `sofd/` 与 GTK 后端未纳入本包验证范围。
5. GTK2 后端（`ui_gtk.c` + `gtk2/`）上游已标注 deprecated 且依赖 GTK2，未在 OHOS 上验证；
   包内保留源码不删（不改变上游行为）。
6. 测试 UI 不含文本组件（仅 dial）：label 的几何与渲染依赖 pango/fontconfig，CI worker 的字体栈不可用（见 §5 #12），因此文本渲染不在包测试中断言；工具箱侧的文本度量已由补丁 0007 加上界保护。

## 10. 验证命令与结果

```bash
# W0 依赖预检
$ bash ci/scripts/preflight_check.sh robtk/0.8.6 \
    --deps "cairo/1.18.4 pango/1.50.14.1.1 glib/2.84.0.1 lv2/1.18.11-git"
[OK] 已发布: cairo/1.18.4 / pango/1.50.14.1.1 / glib/2.84.0.1 / lv2/1.18.11-git
[OK] 版本号未被占用: robtk/0.8.6

# R47 语言预检
$ python3 scripts/ohc-run.py lang-preflight robtk 0.8.6 --src $BUILD_SRC_DIR
✅ 语言匹配: task=cpp, detected=c — 继续适配主流程
   （证据: 源文件 13 个（c:12, cpp:1），主体占比 92%，无语言 manifest，构建系统 none）

# 补丁生成
$ python3 scripts/ohc-run.py refresh-patch --auto robtk 0.8.6
✅ 生成 8 个补丁（orig hash 8d2e421fc3a9d57f → work hash 17b95be773c31e2d；权威值见 manifest.yaml 的 patch_generation 段）

# W3 同源验证
$ conan create archives/r/robtk/0.8.6 -pr:h=ci/conan/profiles/ohos-aarch64 \
    -pr:b=ci/conan/profiles/ohos-aarch64 --build=robtk/*
rc=0（两个测试可执行文件真实运行，60 项断言全通过）
```

## 11. 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | header-library 配方：应用 8 个补丁、打包源码/头文件/robtk.mk、导出 include/defines/system_libs |
| conandata.yml | 官方源 URL + SHA256 + 补丁声明 |
| patches/*.patch | 8 个适配补丁（新增 OHOS 后端 + GLES 呈现层 + 宿主接口 + 文本度量约束 + make 接线） |
| test_package/CMakeLists.txt | 按上游用法编译工具箱（`RW=<robtk 目录>`、`PLUGIN_SOURCE`） |
| test_package/test_pugl_ohos.c | 鸿蒙特有测试：后端层 29 项断言 |
| test_package/test_robtk_ui.c | 全栈测试：LV2 入口 + 组件 + GLES + 输入 + 生命周期 31 项断言 |
| test_package/robtk_test_ui.c | 测试用插件 UI 源码（PLUGIN_SOURCE） |
| test_package/MANIFEST.yml | 上游测试申报（0 项）+ 测试用例声明 |

## 12. 最终状态

- 状态标记：`status: built`
- 编译结束：2026-09-26，`conan create` 退出码 0（W3 通过），两个测试可执行文件真机执行、
  60/60 断言通过。
- 适配结论：robtk 的组件/布局内核在 HarmonyOS 上原样可用；平台差异（无 X11/GLX、无桌面 GL）
  已通过新增 EGL + OpenGL ES 后端彻底解决，离屏 pbuffer 路径使该 UI 代码可在无显示器环境
  持续验证。
- 遗留（不阻塞交付）：GTK2 后端与 `sofd/` 文件对话框未纳入 OHOS 验证范围（见 §9）。
---

**编译结束**: 2026-09-26 17:07
**最终状态**: built
