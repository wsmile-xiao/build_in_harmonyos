# GLES2

## 简介
OpenGL ES 2.0 API 的 C++ 跨平台封装库，将所有 GL 类型、常量和函数封装到 `GL` 命名空间中。提供三种 wrapper：normal（桌面端通过 GLEW 模拟）、qt（通过 QGLFunctions）、dummy（空 stub 实现）。

## OHOS 适配

> ⚠️ **注意：本库使用 dummy wrapper（空 stub 实现），所有 GL 函数不执行任何实际渲染操作。**
> 适用于无原生 OpenGL ES 桌面环境的 HarmonyOS 平台，仅满足编译期符号链接需求。
> 上层应用在运行时不会有任何实际渲染能力，调用方需知晓此限制。

- 上游使用自定义 Yip 构建系统，在 Conan `source()` 方法中动态生成 CMakeLists.txt 替代
- 使用 dummy wrapper（空 stub 实现）适配 HarmonyOS（无原生 OpenGL ES 桌面环境）
- 无外部依赖，纯 C++ 标准库
- 静态库构建（libgles2.a），硬编码 STATIC（不支持 shared 选项）

## 依赖
- 无

## 功能验证
```bash
# 链接 libgles2.a 并调用 GL API
GL::init();
GL::Enum err = GL::getError();  // dummy 返回 GL_INVALID_OPERATION
GL::Int vendor = GL::getInteger(GL::VENDOR);  // dummy 返回 0
```

## 参考
- 源码: https://github.com/yiptool/gles2
