# header-only C 图形库在 HarmonyOS 上的 EGL/GLES3 适配（RSGL 1.12）

> 草稿（DRAFT）。与同目录 `DRAFT-rsgl-1.12-es3-egl-header-only-graphics.kv` 成对。

## 现象

用 OHOS 工具链编译 RSGL（Riley's Simple Graphics Library，header-only C 图形库，
捆绑 RGFW 窗口后端）时：

```text
RSGL.h:278: fatal error: 'X11/Xlib.h' file not found
```

即使绕开窗口后端，后续还会依次出现：

```text
ld.lld: error: undefined symbol: glBegin          （链接期）
Vertex Shader failed to compile: Language version '330' unknown, only '320 es'   （运行期）
RSGL_initGraphics() SIGSEGV                        （运行期，ES3 下 VAO *SRC 指针为 NULL）
```

## 根因

1. **RGFW 在 unix 上无条件依赖 X11**：`deps/RGFW.h` 对 `__unix__` 直接
   `#define RGFW_X11` + `#include <X11/Xlib.h>`。OHOS 无 X11，默认编译必败。
   RSGL 提供 `RSGL_NO_RGFW` 独立图形模式（无窗口、外部 loader），这是 OHOS 正解。
2. **默认 GL 版本自动补全未排除 ES**：`RSGL_gl.h` 用
   `#if !21 && !33 && !43` 自动补 `RSGL_OPENGL_33`；定义 `RSGL_OPENGL_ES3` 后，
   顶点/片段 shader 字符串同时生成 `#version 330` 与 `#version 300 es` 两段声明，
   OHOS GLES 编译器只支持到 `320 es` → 编译失败。
3. **ES3 缺 loader 分支**：VAO 函数（glGenVertexArrays 等）被宏映射到 `*SRC` 指针，
   但 `RSGL_loadGLModern` 的加载分支排除 ES3 → `*SRC` 为 NULL，init 时崩溃。
4. **legacy 立即模式无条件编译**：`RSGL_renderBatch` 的固定管线分支引用
   `glBegin/glEnd/glVertex3f`，GLES2/3 无立即模式 → 链接失败。
5. **独立模式契约**：`RSGL_NO_RGFW` 要求使用者定义按键常量
   （RSGL_BackSpace/Tab/Left/Right/Up/Down）与 `RSGL_isPressedI` /
   `RSGL_window_setMouseStandard` 两个回调（上游文档明示）。

## 解决方案（rsgl 1.12 补丁，全部用库自身功能宏、不引入 `__OHOS__`，R8/PF5 合规）

1. **默认版本逻辑**：
   ```c
   #if !defined(RSGL_OPENGL_21) && !defined(RSGL_OPENGL_33) && !defined(RSGL_OPENGL_43) \
       && !defined(RSGL_OPENGL_ES2) && !defined(RSGL_OPENGL_ES3)
   #define RSGL_OPENGL_33
   #endif
   ```
2. **ES3 shader 变体**（V/F 两段）：`#version 300 es` + `precision mediump float` +
   `in/out` 语义；片段主分支 `#if defined(RSGL_OPENGL_33)||defined(RSGL_OPENGL_ES3)`
   用 `texture()` + `out vec4 finalColor`，否则 `texture2D()` + `gl_FragColor`。
3. **loader VAO 补分支**：
   ```c
   #elif defined(RSGL_OPENGL_ES3)
   RSGL_PROC_DEF(proc, glBindVertexArray);
   RSGL_PROC_DEF(proc, glGenVertexArrays);
   RSGL_PROC_DEF(proc, glDeleteVertexArrays);
   ```
4. **legacy 立即模式编译期排除**：块首尾 `#if !defined(RSGL_OPENGL_ES2) && !defined(RSGL_OPENGL_ES3)` / `#endif`。
5. **消费者测试补契约**：定义按键常量 + 两个回调（headless 下返回明确结果，不伪造输入）。

## 验证（rsgl 1.12，实际运行）

- 消费者测试（`test_package/test.c`）：EGL 1.4 pbuffer 无头上下文 + GLES3，
  `eglGetProcAddress` 为 loader → `RSGL_initGraphics` → `RSGL_graphics_clear` +
  `RSGL_drawRect`（公开 API）→ shader 编译成功 → `glReadPixels` 回读像素 →
  `RSGL_rectCollidePoint` 碰撞命中/未命中。输出：
  ```
  PASS: EGL 1.4 pbuffer context current
  Vertex Shader compile successfully.
  Fragment Shader compile successfully.
  probe pixel at (16,16): R=255 G=255 B=255 A=255
  PASS: RSGL_rectCollidePoint hit=1 miss=0
  CONSUMER TEST DONE        (exit 0)
  ```
- `ohc-run.py conan-verify rsgl 1.12 --profile ohos-aarch64`：G1-G4 + L2/L4/L5 全 PASS。

## 范围与限制

- 适用于捆绑 X11 窗口后端（RGFW/GLFW/SDL 类）的 header-only 图形库移植到无 X11 平台；
  SHADER/loader/立即模式三件套可跨库复用（raylib 的 GLFW 后端同理）。
- ES3 适配基于 GLES3 上下文；若目标设备仅 ES2，shader 需对应 `#version 100` 变体。
- 文本（RFont）与图片（stb_image）等可选模块可视需要保留或裁剪。
- 无头验证覆盖渲染管线与公开 API 可调用性；真实窗口显示需应用侧再接入 OHOS native window。