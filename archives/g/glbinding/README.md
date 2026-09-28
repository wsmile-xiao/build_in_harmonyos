# glbinding

A C++ binding for the OpenGL API, generated from the Khronos OpenGL XML
specification（由 Khronos OpenGL XML 规范生成的 OpenGL C++ 绑定库）。

## 简介

glbinding 提供类型安全的 C++ OpenGL 绑定：所有 GL 函数、枚举与常量均为
编译期类型化，支持函数指针回调、日志与调试回调，是 CG Internals 出品、
基于 gl.xml 自动生成的跨平台绑定层。官方仓库：https://github.com/cginternals/glbinding

## OHOS PC (HarmonyOS aarch64) 适配

- **构建系统**: CMake（上游根工程直接构建，无需代码生成——绑定源码随 tag 附带）
- **产物**: 静态库 `libglbinding.a` + `libglbinding-aux.a`（默认 BUILD_SHARED_LIBS=OFF）
- **工具链**: OHOS NDK `ohos.toolchain.cmake` 直接驱动（CMAKE_SYSTEM_NAME=OHOS），
  显式 `-D` 传递 BUILD_SHARED_LIBS/OPTION_* 防止根 CMakeLists `option(..., ON)`
  默认值覆盖；llvm-ranlib 缺失时使用 `/data/service/hnp/bin/llvm-ranlib`（指向 llvm-ar）
- **运行依赖**: 仅 libc/libdl；GL 入口由消费者通过自有 getProcAddress 注入
  （OHOS 系统 GL 实现为 `/system/lib64/libGLESv3.so` 与 `libEGL.so`，
  鸿蒙专项测试已验证两库可加载、符号可解析）
- **不含 CLI**: 上游 tools（glinfo 等）依赖 glfw3 与真实 GL 上下文，非库交付物
  （R38：纯库包不需要 commands.json）

## 编译状态

| 版本 | 状态 | 补丁 | 备注 |
|------|------|------|------|
| 3.5.0 | ✅ built | 0 | 静态库交付；上游测试 16/18 全量口径（16 注册全部通过），test_package 消费者测试 + 鸿蒙专项测试通过 |

## 依赖

- CMake >= 3.15
- 无第三方库依赖（核心库仅需 KHR 头文件，通过 `OPTION_BUILD_OWN_KHR_HEADERS=ON` 自带）

## 测试

- 上游 glbinding-test（gtest 体系）：16 个注册用例全部通过（RingBuffer 7 / SharedBitfield 3 / Regression 4 / 编译类 2）
- test_package：消费者 API 测试（Meta::getString / Version）+ 鸿蒙专项测试（GLESv3/EGL 加载与符号解析）

## 已知问题

- 上游 2 个未注册测试源（MultiContext_test.cpp / MultiThreading_test.cpp）依赖
  `glbinding/Meta.h`（官方树中不存在，Meta.h 属 glbinding-aux 命名空间）且需要
  多 GL 上下文/真实窗口，保持 uninstantiated（计入源码声明 18 口径分母）。
