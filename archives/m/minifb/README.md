# MiniFB

MiniFB 是一个迷你跨平台窗口框架（emoon/minifb，MIT）：创建 framebuffer 窗口、读写像素缓冲、接收键盘/鼠标/滚轮输入，零第三方依赖（X11/Wayland/Win32 原生 API 后端）。C 接口 + 薄 C++ 包装。

## 功能概述
- 单窗口 framebuffer：mfb_update 提交像素缓冲（RGB/RGBA 格式）
- 输入：键盘（key states + 回调）、鼠标（位置/按键/滚轮/触摸解码）
- 精确计时：mfb_timer_*（clock_gettime 桥）、target fps 调节
- 多平台后端：X11/Wayland/Win32/macOS(Metal)/iOS/Android/Web/DOS
- viewport 缩放、DPI/monitor scale 查询

## OHOS 适配（headless 核心契约）
OHOS PC 无 X11/Wayland 会话，窗口创建（mfb_open）**不支持**——headless 处置：
- **可用**：软件帧缓冲接口测试（mfb_update 状态机）、完整 timer API（clock_gettime）、NULL 窗口安全输入 getter、utf8 助手
- **豁免申报**：mfb_open_ex 返回 NULL（无窗口系统，stub 如实行为）；examples 交互式演示不构建
- 补丁：CMake 识别 HarmonyOS 为类 Linux + X11 连锁关闭 + 注入 linux 计时器源；4 个窗口入口的 headless stub（配方侧源文件）

## 依赖关系
- **编译依赖**: 无
- **运行依赖**: 无（libc/clock_gettime）

## 参考资料
- 官网: https://github.com/emoon/minifb
