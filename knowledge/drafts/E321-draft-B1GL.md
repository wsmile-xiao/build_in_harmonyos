# 【知识库扩展】OHOS PC 缺桌面 OpenGL(libGL) 时用 gl4es 提供 libGL.so 兼容层适配固定管线 GL 软件

> 对应结构化数据：`knowledge/drafts/E321-draft-B1GL.kv`
> 详细过程与踩坑清单：`archives/a/assaultcube/1.3.0.2/reports/offscreen-render-process.md`
> 验证实例：AssaultCube 1.3.0.2（OHOS PC aarch64，SDK 26，GPU=HUAWEI Maleoon 916）

## 1. 知识库名称

**OHOS 桌面固定管线兼容层（gl4es → libGL.so）**

## 2. 问题背景

OpenHarmony PC 只提供 **OpenGL ES 3.2（`libGLESv3.so`）+ EGL**，**没有桌面 OpenGL（`libGL.so`）**。
任何依赖**桌面 OpenGL 固定管线 / 立即模式**的三方库或游戏，在 OHOS 上适配时会在多处失败：

- 链接期：`cannot find -lGL`（无 libGL.so；`libGLv4.so` 实为 stub——全符号同地址，无固定管线实现）。
- 运行期：没有可用的桌面 GL 上下文（GLES 无 `glBegin/glMatrixMode/glOrtho/客户端顶点数组/矩阵栈/纹理环境/光照/雾`）。

已遇到的具体实例：assaultcube（Cube1 引擎，纯固定管线）、asymptote（无 libGL 而 `--disable-gl`）、
aegisub（wxGLCanvas 预览）、irrlicht（禁 GL，走 EDT_NULL）、以及大量老式固定管线 GL 游戏/图形软件。

## 3. 问题根因

不是平台"能力缺失"，而是**缺一个可移植的库层**：

- OHOS **有**真实 GLES3.2 硬件 + EGL 窗口表面 + Mesa gallium（`libEGL_mesa.so` 依赖 `libgallium-25.0.1.so`），只是**未暴露桌面 GL**。
- 桌面 GL 固定管线可用 **gl4es**（OpenGL 1.5/2.1 → GLES2 翻译库，内置 FPE 固定管线模拟）补齐。
- 因此属 **B1（可复用通用方案）**，而非 B2「无法适配」——注意 B 规则：**"依赖没移植" ≠ "鸿蒙无法适配"**。

## 4. 适用范围

适用：
- OHOS PC / HarmonyOS aarch64（armv8）。
- 依赖**桌面 OpenGL 固定管线 / 立即模式**（非 shader 化）的库：老式 3D 游戏、图形软件、GUI 里的 OpenGL 预览（wxGLCanvas 等）。

不适用：
- 用 **shader / 现代 GL 管线**（glCreateShader/glVertexAttrib/glUniform/FBO）的应用——gl4es 的 shader 转换较简陋，此类应改写作 GLES3/GLSL。
- 需要**可见窗口**的场景：OHOS 可见窗口强绑定应用框架（ArkUI/XComponent），裸进程拿不到 `OHNativeWindow`。本方案只解决"能在 GLES3 上渲染出来"。

## 5. 输入

- 项目类型：C/C++，构建系统 cmake/make/autotools。
- 链接目标带 `-lGL`（或运行期需桌面 GL 上下文）。
- 相关日志：`cannot find -lGL`、`Could not load EGL library`、`Could not initialize OpenGL / GLES library`、`glDrawRangeElementsEXT not found`。

## 6. 输出

- **gl4es** 构建产物：`libGL.so`（+GL 头/`gl4esinit.h`），作为 `-lGL` 的替代。
- 运行环境变量：`LIBGL_GLES=/system/lib64/libGLESv3.so`、`LIBGL_EGL=/system/lib64/libEGL.so`（OHOS 无 `libGLESv2.so`）。
- 消费方"可选 GL 扩展按函数指针是否解析成功"启用（防御性）。

## 7. 解决方案

1. **gl4es 提供 libGL.so**（补 `-lGL`）：
   ```bash
   cmake -S . -B build -DNOX11=ON -DNOEGL=OFF -DSTATICLIB=OFF -DDEFAULT_ES=2 -DCMAKE_SYSTEM_NAME=Linux
   cmake --build build && ln -sf libGL.so.1 lib/libGL.so
   export LIBGL_GLES=/system/lib64/libGLESv3.so   # OHOS 无 libGLESv2.so
   export LIBGL_EGL=/system/lib64/libEGL.so
   ```
   - 关键选项：`CMAKE_SYSTEM_NAME=Linux`（gl4es 只在匹配 "Linux" 时才编译 GLX/EGL 后端）；`NOX11=ON`（OHOS 无 X11）；`DEFAULT_ES=2`（GLES2 后端，兼容 GLES3 硬件上下文）。
   - 上游无 `install()`（写死 `/usr/lib/gl4es/`）→ 手动复制 `libGL.so*` + include 并建 `libGL.so → libGL.so.1` 软链。
2. **消费方**：可选 GL 扩展以"函数指针是否解析成功"决定是否启用（`hasDRE = glDrawRangeElements_ != NULL` 等），避免 gl4es 缺 EXT/ARB 后缀名导致崩溃。

## 8. 使用方法

1. 构建 gl4es 得 `libGL.so`，放入消费方链接路径（`-lGL` 解析到它）。
2. 运行时设 `LIBGL_GLES=/system/lib64/libGLESv3.so`、`LIBGL_EGL=/system/lib64/libEGL.so`。
3. 消费方里"可选扩展按函数指针启用"（防御性）。
4. 离屏验证：EGL pbuffer GLES2 上下文 + gl4es 固定管线（`glBegin/glEnd/glMatrixMode/glColor3f/glVertex3f`）+ `glReadPixels` 校验非黑。

## 9. 示例（AssaultCube）

- 链接：`make client CLIENT_LIBS="... -lGL(→gl4es) ..."`，产出 `ac_client`。
- 运行：`Renderer: GL4ES using Maleoon 916 (GL4ES wrapping HUAWEI)` / `Driver: 2.1 gl4es wrapper 1.1.7`。
- 出图：`profile/screenshots/ac_run.jpg`（1024x768）。

## 10. 通用性说明

这不是 assaultcube 的特例补丁，而是**一类问题**的通用解法：OHOS 无桌面 GL → 用 gl4es 补 libGL。
可被**任何**"依赖桌面 GL 固定管线"的库复用；"可选扩展按函数指针启用"是跨兼容层的通用防御。
同类先例：asymptote/aegisub/irrlicht 均因"无 libGL"受阻，可套用。

## 11. 验证结果

- gl4es 直连测试：`glGetString=2.1 gl4es wrapper 1.1.7`、`GL_VENDOR=GL4ES wrapping HUAWEI`、`GL_RENDERER=GL4ES using Maleoon 916`、执行固定管线序列后 `glGetError()=GL_NO_ERROR`。
- test_package R34 离屏渲染 PASS（`nonblack=512/4096`、`glGetError=0x0`）。
- AC 客户端：本机 GLES3.2(Maleoon 916) 上 `init: gl` 成功，渲染出图（截图铁证）。

## 12. 结论

OHOS PC 缺的是**缺一个可移植的库层（桌面 OpenGL/libGL）**，而非平台能力缺失。用 **gl4es 兼容层**可让**依赖桌面 OpenGL 固定管线**的库/游戏在 OHOS 真实 GLES3 硬件上**真正渲染**。这属 **B1 知识库扩展（可复用通用方案）**；"弹窗可玩"需另走 OHOS 应用框架（ArkUI/XComponent）。
