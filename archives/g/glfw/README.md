# glfw

A multi-platform library for OpenGL, OpenGL ES, Vulkan, window and input.

## 简介

GLFW 是一个用于 OpenGL、OpenGL ES 和 Vulkan 开发的轻量级、开源、多平台库。它提供了用于渲染、输入和上下文管理的简单 API。

## 编译状态

| 版本 | 状态 | 补丁 | 备注 |
|------|------|------|------|
| 3.5.1 | ✅ published | 1 | 上游原版 Null-only 后端（无头 GLFW，libglfw.so.3.5），posix_time.c time.h 补丁 + _DEFAULT_SOURCE |
| 3.4 | ✅ published | 1 | HMDFS mktemp 临时目录权限问题修复 |
| 3.4.6 | 🔨 built | 0 | ohos_native_glfw fork：XComponent + 桌面 GL，two-pass 双 .so（libglfw.so.3 + libglfw_bridge.so） |

## 版本选择指引

- **3.5.1（上游原版 Null-only）**：无窗口系统依赖的无头 GLFW——`glfwInitHint(GLFW_PLATFORM, GLFW_PLATFORM_NULL)`
  后即可用窗口/监视器/输入/时间 API（ 平台模拟监视器与窗口对象），适合 CI、服务器端、单元测试、
  Vulkan 计算等场景。产物含 EGL/OSMesa 上下文支持代码（运行期 dlopen，按需）。
- **3.4.6（ohos fork XComponent）**：需要真实窗口渲染的 HAP 应用集成（XComponent + 桌面 GL）。

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