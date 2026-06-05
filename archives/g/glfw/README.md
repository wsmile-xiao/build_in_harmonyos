# glfw

A multi-platform library for OpenGL, OpenGL ES, Vulkan, window and input.

## 简介

GLFW 是一个用于 OpenGL、OpenGL ES 和 Vulkan 开发的轻量级、开源、多平台库。它提供了用于渲染、输入和上下文管理的简单 API。

## 编译状态

| 版本 | 状态 | 补丁 | 备注 |
|------|------|------|------|
| 3.4 | ✅ published | 1 | HMDFS mktemp 临时目录权限问题修复 |

## 依赖

- CMake >= 3.10
- 无第三方库依赖（可选：X11、Wayland）

## 已知问题

### OpenHarmony 平台

1. **HMDFS mktemp 权限问题**：临时目录创建需要指定 `TMPDIR` 环境变量
   - 解决方案：补丁修改 `src/posix_time.c` 使用 `getenv("TMPDIR")`

## 参考

- 官方文档：https://www.glfw.org/documentation.html
- GitHub：https://github.com/glfw/glfw