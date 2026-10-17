# seexpr

Disney/Pixar 的嵌入式表达式语言库（SeExpr），用于程序化图形（着色、粒子、图像合成等场景）中以类 C 表达式驱动参数。

## 功能概述

- 解释器核心（libSeExpr2）：表达式解析（flex/bison 生成的 parser）、类型系统、内置函数库（数学/噪声/曲线等）
- 可选组件（本适配未启用）：Qt5 表达式编辑器 UI、Python 绑定、LLVM JIT 后端、图像合成 demos

## OHOS 适配

- 目标：HarmonyOS PC aarch64，产出共享库 libSeExpr2.so
- 关键适配点：
  - `ENABLE_SSE4=OFF`（aarch64 无 SSE4.1，走 Noise.cpp 便携路径）
  - CMake 无 Platform/HarmonyOS 模块，toolchain 层补 DT_SONAME
  - parser 需构建期用 flex/bison 重新生成（tarball 不含预生成文件）
  - gtest 1.17 要求 C++14+，上游写死 -std=c++11 需提升到 c++17
- 已知限制：不含 Qt5 UI、Python 绑定、LLVM JIT（依赖未发布/旧 API）

## 依赖关系

- 运行依赖：无第三方（仅 libc/libc++）
- 测试依赖：libpng、gtest（test_requires）
- 构建工具：bison、flex、m4（tool_requires，OHOS worker）

## 参考资料

- 上游仓库：https://github.com/wdas/SeExpr
- 文档：https://wdas.github.io/SeExpr/
