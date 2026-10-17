# minifb 0.13.0 适配笔记

## 软件信息
- 软件：minifb 0.13.0（上游 emoon/minifb tag **v0.13.0**——注意有 v 前缀，0.13.0 无前缀 404；MIT）
- 定位：迷你跨平台窗口框架（framebuffer 窗口 + 键鼠输入）——C，多后端（X11/Wayland/Win32/macOS/iOS/Android/Web/DOS）
- 构建系统：上游 CMakeLists（按 CMAKE_SYSTEM_NAME 分平台编源）
- 分支 feat/minifb-0.13.0；worktree ~/huawei/worktrees/j669539/minifb-0.13.0

## W0/W0b
- W0 preflight：PASS（零外部依赖——窗口后端全关后纯 C 核心+libc）
- W0b：本仓库无 minifb 历史归档
- lang-preflight：c 判定（src/ 主体 C；MiniFB_cpp.cpp 是薄 C++ 包装）

## OHOS headless 处置（核心适配——如实申报）
OHOS PC 无 X11/Wayland 会话，窗口创建（mfb_open_ex）**不支持**——按 headless 处置：
1. **patch 0001**：①CMakeLists 识别 HarmonyOS 为类 Linux（内核/musl 同源）②两个 CMake 版本分支的 X11 连锁在 OHOS 下关闭（否则 find_package(X11) FATAL）③SrcLib 按 PLATFORM_ID=HarmonyOS 注入 src/MiniFB_linux.c（clock_gettime 计时器——OHOS clang 预定义 __linux__，上游守卫代码天然可编译）
2. **MiniFB_ohos_stub.c**（配方侧源文件，exports_sources 携带）：4 个窗口后端入口的 headless 实现——mfb_open_ex→NULL（如实：无窗口系统）、mfb_update_ex→INVALID_WINDOW、mfb_set_viewport→false、mfb_get_monitor_scale→恒等缩放
3. **可用 API 面（headless 核心契约）**：软件帧缓冲接口测试全部可跑——mfb_update 状态机（含错误路径）、完整 timer API（mfb_timer_create/reset/now/delta/destroy、set/get_target_fps、frequency/resolution）、NULL 窗口安全的输入 getter（mouse_x/y/scroll）、utf8 助手
4. **真窗口相关豁免申报**：mfb_open/mfb_open_ex 返回 NULL（无窗口系统）；examples 全部为交互式窗口演示（noise/multiple-windows 等，需显示器+键鼠）不构建不执行——豁免证据：OHOS 无 X11/Wayland 会话，mfb_open_ex stub 返回 NULL 即为运行时如实行为

## 源码检查（上游 v0.13.0 tarball，SHA256 6e38ec1c5fdf6cf868156bc87c9f43b867c85448d5ae55e77cdc12781af3ba08）
- src/MiniFB_common.c+internal.c+timer.c+cpp.cpp：平台无关核心
- src/x11|wayland|windows|macos|ios|android|web|dos/：平台后端
- 上游无自动测试注册（无 add_test；examples 为交互演示）
- 补丁 1 个（portability）+ 配方侧 stub 源 1 个

## 上游测试统计与执行（rule4 口径）
- 上游注册自动测试：**N=0**（无 add_test/enable_testing；examples 8 个为交互式窗口演示非测试）
- 上游验证形态=库构建：本地 conan create 全绿

## 适配后测试（消费者，test_package）
- test_minifb.c 13 项断言全过（failures=0）：
  - mfb_update(NULL)→MFB_STATE_INVALID_WINDOW（文档化错误路径）
  - set/get_target_fps 60 往返
  - timer 全 API：create/reset/now/delta/destroy（clock_gettime 桥，实测 now=0.0146s delta 推进）
  - NULL 窗口输入 getter：mouse_x/y/scroll_x 全 0
  - frequency>0 / resolution∈(0,1)

## OHOS 平台要点
- __linux__ 在 OHOS clang 目标预定义（与 __OHOS__ 并存）——上游 linux 计时器代码直接可用
- CMAKE_SYSTEM_NAME=HarmonyOS 时 LINUX 变量不 set——上游静默跳过所有后端（链接缺符号），必须 patch 识别
- 测试二进制运行需 E077 签名

## 验证记录
- conan create（G2）+ test_package 全链路本地通过（13/13 断言）
- status：built（上传发布须等合并后 release 流水线）
