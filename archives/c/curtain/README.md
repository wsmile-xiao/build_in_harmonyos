# curtain

Curtain 0.3（GTK3 桌面遮罩小工具）的 HarmonyOS PC 适配。拖拽揭开幕布边缘、揭开区域点击穿透、
右上角关闭；用于演示时遮盖屏幕内容。GPL-3.0-or-later，原项目 Pietro Pilolli（Google Code ardesia）。

- 上游历史归档（官方源）:
  https://storage.googleapis.com/google-code-archive-downloads/v2/code.google.com/ardesia/curtain-0.3.tar.gz
  SHA256 a361bf9edb85c35b9080458b9d68abae409825837f8a24207a9e62ea43950adb
- 类型: application（`package_type=application`；commands.json 已声明）
- 版本目录: 0.3/

## OHOS 适配要点

- OHOS 已发布 GTK 只有 Broadway 后端（浏览器内显示），无法覆盖原生桌面。适配保留上游源码不动，
  新增 ArkUI 原生宿主（`harmony/project`）承载窗口与触摸，上游 `callbacks.c` 的拖拽几何状态机
  与 `utils.c` 的缩放语义移植到 C 核心（`curtain_core.c`），经 NAPI 供 ArkTS 调用。
- 窗口矩形即幕布矩形：拖拽释放后调整窗口 move/resize，窗户外即桌面，天然实现揭开与点击穿透。
- `setWindowTopmost` 需系统权限（普通应用不可用），无置顶时其他窗口可能盖住幕布，核心行为不受影响。
- 上游无自动化测试（N=0）；消费者侧以 `bin/curtain_check`（28 项几何/缩放断言）与
  包结构检查替代，另有真机功能验证记录（见 0.3/notes.md 与 reports/）。

## 依赖

无 Conan 运行时依赖；构建使用 OHOS SDK clang 15 与 CMake。
