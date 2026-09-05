# portablegl

**PortableGL — Portable OpenGL**

纯 C99 实现的 OpenGL 3.x core 子集软件光栅化库，以 stb 风格单头文件发布。CPU 渲染，无 GPU、无窗口系统依赖。

## 基本信息

- **版本**: 0.100.0（2026-03-05 上游最新稳定 release）
- **许可证**: MIT
- **网站**: https://github.com/rswinkle/PortableGL
- **类型**: Header-only 库（单头 portablegl.h，13097 行，实现全部内联）
- **依赖**: 零第三方依赖（仅需 libc + libm）

## 已编译版本

| 版本 | 状态 | 编译日期 | 补丁数 |
|------|------|---------|--------|
| 0.100.0 | built | 2026-09-03 | 0 |

## 特性

- OpenGL 3.x core profile API 子集（glGenBuffers/glDrawElements/shader 内建等）
- shader 为 C/C++ 函数（免 GLSL 解析器），uniform 通过结构体指针传递（pglSetUniform）
- 任意 32/16 位帧缓冲格式（PGL_ABGR32 默认，RGB565、ARGB32、BGRA32 等可编译期选择）
- 软件光栅化：离屏渲染到内存帧缓冲，适合无 GPU 环境、测试与嵌入场景
- C99 编写，可作为 C 或 C++ 使用

## 使用方法

```c
#define PORTABLEGL_IMPLEMENTATION   /* 恰好一个翻译单元中定义 */
#include "portablegl.h"

pix_t* framebuffer = NULL;
glContext ctx;
init_glContext(&ctx, &framebuffer, 320, 240);  /* 离屏内存帧缓冲 */
glClearColor(0, 0, 1, 1);
glClear(GL_COLOR_BUFFER_BIT);
/* ... 渲染 ... 读 framebuffer 像素 ... */
free_glContext(&ctx);
```

Conan 消费（cmake_target_name `portablegl::portablegl`）。

## OHOS PC 适配要点

1. Header-only：`package_type="header-library"`，无 cpp_info.libs，package_id 清空
2. 上游无构建系统（无 configure/CMakeLists）——testing/ 用 premake 生成的 makefile
3. 离屏渲染路径已全量实测：上游 6 套件 625 项测试全过（clang 15.0.4 原生 arm64），含像素级 PNG 对比
4. test_package 实质调用渲染 API：init_glContext → glClear 蓝色断言 → glDrawElements 红色四边形断言（6 项像素断言）
5. demos/examples 依赖 SDL2/GLFW/等窗口后端，OHOS PC 无对应窗口系统，跳过（不影响库本体适配完整性）

## 依赖

- 无外部依赖（纯 C99 + libm）
