# SFML - Simple and Fast Multimedia Library

## 简介

SFML (Simple and Fast Multimedia Library) 是一个跨平台的多媒体库，提供简单易用的 API 来访问：

- **System 模块**：线程、时间、字符串处理等基础功能
- **Window 模块**：窗口管理和输入处理
- **Graphics 模块**：2D 图形渲染
- **Audio 模块**：音频播放和录制
- **Network 模块**：网络通信

SFML 广泛应用于游戏开发、多媒体应用和教育领域。

## HarmonyOS 适配状态

| 模块 | 状态 | 说明 |
|------|------|------|
| System | ✅ 可用 | 基础系统模块已适配 |
| Network | ✅ 可用 | 网络 TCP/UDP 模块已适配 |
| Window | ❌ 未适配 | 需要 X11 或 DRM + UDev 支持 |
| Graphics | ❌ 未适配 | 依赖 Window 模块 + OpenGL ES |
| Audio | ❌ 未适配 | 需要 OpenAL 库支持 |

### 适配说明

1. **Window 模块**：HarmonyOS 不支持 X11 窗口系统，需要实现 DRM/KMS 后端或使用 HarmonyOS 原生窗口 API
2. **Graphics 模块**：依赖 Window 模块提供渲染上下文，需先完成 Window 适配
3. **Audio 模块**：需要编译 OpenAL 或使用 HarmonyOS 原生音频 API

### 已解决的问题

- CMake 平台检测：添加 HarmonyOS 支持
- pthread 线程取消：HarmonyOS 缺少 `pthread_cancel`，`sf::Thread::terminate()` 为 no-op（保持 joinable，等待线程自然结束）
- OpenGL ES 支持：Window/Graphics 模块已禁用（`SFML_BUILD_WINDOW=OFF`/`SFML_BUILD_GRAPHICS=OFF`），无需 EGL/GLES 适配

## 编译信息

- **构建系统**：CMake
- **编译器**：clang/clang++
- **编译选项**：
  - `SFML_BUILD_AUDIO=OFF` - 禁用音频模块
  - `SFML_BUILD_WINDOW=OFF` - 禁用窗口模块
  - `SFML_BUILD_GRAPHICS=OFF` - 禁用图形模块

## 已编译版本

| 版本 | 状态 | 日期 |
|------|------|------|
| 2.6.1 | built（System/Network） | 2026-07-19 |

## 使用方法

```bash
# 安装预编译包
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- sfml 2.6.1

# 链接库
# libsfml-system.so
# libsfml-network.so

# CMake 配置
find_package(SFML COMPONENTS system network REQUIRED)
target_link_libraries(your_target sfml-system sfml-network)
```

## 相关资源

- 官方文档：https://www.sfml-dev.org/learn.php
- API 参考：https://www.sfml-dev.org/documentation/
- GitHub：https://github.com/SFML/SFML

## 注意事项

1. 当前仅支持 System 和 Network 模块
2. 如需完整的图形功能，需等待 HarmonyOS 窗口系统适配
3. 网络模块已通过基本功能测试