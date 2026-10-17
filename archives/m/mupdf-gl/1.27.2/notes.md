# mupdf-gl 1.27.2 适配笔记

## 编译环境
- 构建系统: makefile（自定义 Makefile，与 mupdf/1.25.1 同构）
- 编译日期: 2026-09-28（W3 全流程 conan create 复验，TEST-PASS）
- 编译器: clang/clang++（OHOS SDK 26.0.0.18，clang 15.0.4，本机即设备）
- 状态: built（成功）

## 配方形态（库形态，非完整查看器）
本包交付**库形态**：
- `make libs` 产出 libmupdf.a + libmupdf-third.a（+ build() 内 brotli 归档修复）
- 打包适配后的 GL 渲染源 gl-ui.c（VAO 改写版）+ 伴随头 gl-app.h 至
  `include/mupdf-gl-ohos/`，知识随包交付
- package_info 声明 2 个库：`mupdf`、`mupdf-third`（static-only，R26）
- 完整 mupdf-gl 查看器可执行文件（HAVE_GLUT=yes）在 OHOS 上仍有约 13 个
  缺失的固定管线 GL 符号，链接必失败——列为**后续独立任务**
  （缺口清单与工时估算见本笔记末尾）

## 编译步骤

### 1. 源码
GitHub 官方 tarball 端点 codeload.github.com（sha256 固定；codeload 为
github.com archive URL 的官方重定向目标，字节一致；本机 github.com 直连
不稳定——HEAD 实测空响应、GET 时通时断——故选稳定端点）+ 14 个 thirdparty
子模块按精确 commit 下载（13 个复用 mupdf/1.25.1 已验证集合；brotli 为
1.27.2 新增，pin 到 mupdf 1.27.2 子模块 gitlink commit 6e092ab7，确定性
构建）。
注意：conan 2 get() 按文件名后缀选择解压格式（无 magic-bytes 回退，
files.py unzip() 对无后缀文件直接走 zipfile → tar.gz 会 BadZipFile）；
codeload URL basename 无 .tar.gz 后缀，故 conandata sources 与子模块
get() 调用均显式传 filename（mupdf-1.27.2.tar.gz / <dir>.tar.gz）触发
untargz 路径。

### 2. 编译
```bash
make libs CC=clang CXX=clang++ AR=llvm-ar RANLIB=llvm-ranlib \
    HAVE_X11=no HAVE_GLUT=no shared=no build=release \
    HAVE_OBJCOPY=no XLDFLAGS="-fuse-ld=ld" -j2
```
- `make libs`（非默认 target）：默认 target 会构建 mutool/muraster 可执行文件，
  其链接受 brotli 归档缺陷影响；`libs` 只产静态库
- 参数说明与 mupdf/1.25.1 相同（HAVE_X11/GLUT=no：OHOS 无 X11/GLUT 窗口系统；
  shared=no：静态，R26；HAVE_OBJCOPY=no：OHOS 无 objcopy，字体嵌入走 hexdump；
  XLDFLAGS=-fuse-ld=ld：CI 的 lld 依赖 libxml2.so.16 不可用）

### 3. brotli 归档修复（1.27.2 新增缺陷）
stock Makefile 将 thirdparty/brotli/c/{common,dec,enc}/*.c 编译为 .o 但未把
全部归档进 libmupdf-third.a → 下游链接 libmupdf.a 时
BrotliDecoderEnsureStaticInit/kStaticDictionaryBuckets 等 undefined。
build() 内用 `llvm-ar q libmupdf-third.a <31 个 brotli .o>` + `llvm-ranlib`
修复（非源码补丁，Makefile 不动）。

## VAO 补丁（本 PR 核心）
`patches/0001-vao-rewrite.patch` 改写 `platform/gl/gl-ui.c` 的 `ui_draw_image()`：

- **原代码**：立即模式 `glBegin(GL_TRIANGLE_STRIP)` + `glVertex2f` +
  `glTexCoord2f` + `glEnd` 绘制页面纹理四角
- **OHOS 现状**：立即模式符号在 libGLESv2.so/libGLESv3.so 导出表 0 命中
  （llvm-nm -D 实测）且 eglGetProcAddress 返 NULL → **未补丁版本链接即失败**
  （undefined symbol，比运行时 NULL 段错误更早暴露）
- **改写**：
  - `ui_ensure_vao()`：惰性一次性初始化 shader（VS passthrough + FS 采样；
    FS 必须 `precision mediump float;`，ES 无默认精度，否则 S0032）+ VAO + VBO
    （glVertexAttribPointer 绑定 a_pos/a_uv）
  - `ui_draw_image_vao()`：`glBufferData`（非 glBufferSubData——ES 中未分配
    VBO 上 sub-data 报 GL_INVALID_VALUE）上传 4 顶点 strip + `glDrawArrays`
  - **坐标系**：原 app 的 ui_begin 用 `glOrtho(0, w, h, 0, -1, 1)`（Y-DOWN
    窗口坐标投影）；VAO 路径无矩阵栈，CPU 侧对 `glGetIntegerv(GL_VIEWPORT)`
    做等价变换 `ndc_x = 2x/vp_w - 1`、`ndc_y = 1 - 2y/vp_h`。顶点坐标直接
    当 NDC 传会导致真实窗口下渲染成角落碎屑（本任务端到端测试曾暴露该缺陷）
  - 删除 `glEnable(GL_TEXTURE_2D)`（ES2/3 非合法 enable cap，GL_INVALID_ENUM；
    纹理单元由 glBindTexture 激活）
- 纹理上传路径（ui_texture_from_pixmap）无需改动

## 依赖
- 库构建：无 conan 依赖（thirdparty 全部内嵌）
- test_package：freeglut/3.6.0（已发布，仅用头文件——gl-app.h 经
  `<GL/freeglut.h>` 引入；freeglut 包定义 -DFREEGLUT_GLES 使 freeglut_std.h
  只 include <GLES2/gl2.h>）

## 验证结果（W3 权威）
`conan create archives/m/mupdf-gl/1.27.2/ -pr:h ohos-aarch64`（2026-09-28，
日志 conan-create6.log）：
- source/build/package 全过：`archived 31 brotli objects`；
  packaged 2 .a + 84 .h + gl-ui.c（含新打包的 gl-app.h）
- test_package（编译**包内真实打过补丁的 gl-ui.c**：-ffunction-sections +
  -fdata-sections + -Wl,--gc-sections 只保留 ui_draw_image 闭包，无需 mupdf
  核心符号即可链接）真机 ES3.2 pbuffer 端到端驱动 `ui_draw_image()`：
  ```
  [egl] EGL 1.4 vendor=OpenHarmony
  [gl] GL_VERSION=OpenGL ES 3.2 B301
  [neg] glBegin=0 glEnd=0 glVertex2f=0 glTexCoord2f=0
  [neg] immediate mode unavailable on this OHOS GLES driver: YES
  [gl] framebuffer nonblack=40000/40000 (100.0%), center=(51,102,204)
  TEST-PASS
  ```
- 合成 pixmap：红底（204,51,51）+ 蓝块（51,102,204，x∈[60,140)×y∈[60,140)），
  1:1 绘制后回读：framebuffer 100% 非黑、中心命中蓝块 → 渲染正确

## 上游测试清点（R51）
- mupdf 1.27.2 顶层 Makefile **无 `test` 目标**（已核对全部规则）；
  仅有 extract-test（thirdparty/extract 子模块测试，不属本配方范围）与
  examples/ 下示例程序（storytest 等）
- platform/gl **无测试 harness**（查看器经 freeglut 交互驱动，无自动化测试）
- 故以端到端 GL 渲染测试补全（见 test_package/，3 断言）

## 构建产物
- libmupdf.a — 静态核心库
- libmupdf-third.a — 第三方静态库（含修复归档的 31 个 brotli 对象）
- include/ — 83 个 mupdf 公共头文件
- include/mupdf-gl-ohos/ — gl-ui.c（VAO 补丁版）+ gl-app.h

## 注意事项（OHOS GL 平台陷阱，本任务真机实测）
1. **立即模式/固定管线不存在**：glBegin/glEnd/glVertex2f/glTexCoord2f/
   glPointSize/glMatrixMode/glLoadIdentity/glOrtho/glNewList/glCallList/
   glDeleteLists/glGenLists/glLineStipple 等在 libGLESv2/v3.so 导出表 0 命中
   → 未移植代码**链接期**即失败（undefined symbol），比运行时更早暴露
2. **libGLESv2.so 是空桩**：673 个符号全部别名指向单一入口 0xa1b0，不工作
   （经 v2 绑定的 glGetString 返 NULL、绘制静默全黑）；libGLESv3.so
   （2942 符号，ES2 核心严格超集）dispatcher 0x5d70 实际工作
   → **只链 -lEGL -lGLESv3，不链 -lGLESv2**
3. **eglGetString 缺失**：libEGL.so 不导出已废弃的 eglGetString（EGL 1.0），
   只有 eglQueryString（EGL 1.5）；lld 报错会误导性提示
   "did you mean: glGetString defined in libGLESv2.so"
4. **默认 ES 1.1 上下文**：必须显式 EGL_CONTEXT_CLIENT_VERSION=3
5. **ES fragment shader 需 precision 语句**（否则 S0032 编译失败）
6. **glBufferData 而非 glBufferSubData**（未分配 VBO 上 sub-data 非法）
7. **CMake 3.16 解析陷阱**：未闭合多行命令体内行内注释里的 `)` 被计入
   括号匹配 → "Parse error. Function missing ending ')'"；注释挪到命令外
8. **FREEGLUT_GLES 头分支**：freeglut 包定义 -DFREEGLUT_GLES →
   freeglut_std.h 只 include <GLES2/gl2.h>（不走 GL/gl.h+GL/glu.h 分支）；
   编译未移植函数需补 5 个固定管线常量（GL_PROJECTION 0x1701 /
   GL_MODELVIEW 0x1700 / GL_COMPILE 0x0F00 / GL_STACK_OVERFLOW 0x0503 /
   GL_STACK_UNDERFLOW 0x0504）+ <GLES3/gl3.h> 声明（方案见
   test_package/CMakeLists.txt 的 glstub 生成 + -include）

## 后续任务：完整 mupdf-gl 查看器移植（约 13 符号缺口，预估 5–10 人日）
1. **字形/批注立即模式绘制**：glBegin/glEnd/glVertex2f/glTexCoord2f/
   glColor3f/glColor4f/glPointSize（gl-font.c/gl-annotate.c 等）→ VAO 批量
   （300–600 行，1–2 天）
2. **显示列表**：glNewList/glCallList/glEndList/glDeleteLists/glGenLists/
   glLineStipple → ES 无显示列表，用 FBO 离屏缓存等价（200–400 行，1 天）
3. **固定管线矩阵**：glMatrixMode/glLoadIdentity/glOrtho（gl-ui.c ui_begin
   的 Y-DOWN 投影）→ CPU 矩阵 + shader uniform（100–300 行，0.5–1 天）
4. **freeglut 剪贴板**：glutGetClipboard/glutSetClipboard → stub 或补实现
   （需 freeglut 发 3.6.0.1，~30 行，0.5 天）
5. **真机验证/调试**：无头环境视觉调试最慢（需 glReadPixels 像素对比
   harness），2–4 天
- 平台任务口径：单任务预算（12h×3 尝试）装不下，需拆 2–3 个任务续跑或
  独立专项（约 1–2 周日历时间）
- **价值提示**：freeglut/3.6.0 的 OHOS 适配是 EGL pbuffer **离屏后端**
  （OHOS 无窗口系统），完整查看器即便移植完成也只渲染到离屏 buffer；
  真实窗口显示需另做 pbuffer→ArkUI/XComponent 桥接。"PDF→图像"能力
  mutool draw 已具备，完整 glut 查看器在 OHOS 的净增量价值有限——若未来
  有嵌入需求，建议路线是 libmupdf + 自绘 GL 层而非 glut 查看器

---
**编译结束**: 2026-09-28 14:35
**最终状态**: built
---

**编译结束**: 2026-09-28 17:30
**最终状态**: built
