# Curtain 0.3 HarmonyOS PC 适配笔记

## 上游与版本

- 软件：Curtain 0.3（GTK3 桌面遮罩小工具，Pietro Pilolli，GPL-3.0-or-later）
- 官方历史归档：
  `https://storage.googleapis.com/google-code-archive-downloads/v2/code.google.com/ardesia/curtain-0.3.tar.gz`
- SHA256：`a361bf9edb85c35b9080458b9d68abae409825837f8a24207a9e62ea43950adb`（下载后核对一致）
- 上游功能：全屏置顶窗口盖住桌面；拖拽幕布边缘揭开区域（剩余幕布恒为矩形，最小 25px）；
  揭开区域不接收输入（点击穿透）；右上角 25px 热区关闭。

## 适配策略与原因

OHOS 已发布的 GTK 3.24.43 仅启用 Broadway 后端（HTML5/浏览器输出），没有 X11/Wayland
等原生显示后端，无法覆盖 HarmonyOS 桌面，因此上游 GTK 窗口层不能直接在真机产生遮罩效果。

本适配保留上游源码不动（补丁只新增文件），把应用行为移植到 HarmonyOS 原生 UI 栈：

- **ArkUI 宿主**（`harmony/project`，DevEco 工程，包名 `com.kasumizawamiyuu.curtainhost`）：
  主窗口全屏沉浸 + 隐藏标题栏，作为幕布窗口；触摸事件转成屏幕坐标驱动 C 核心。
- **C 核心**（`curtain_core.c`）：逐分支移植上游 `src/callbacks.c` 的按压/释放几何状态机
  （四边揭开、回盖、最小尺寸钳制、关闭热区）；缩放逻辑对应上游 `utils.c::scale_surface`，
  由平台 `image` 模块解码 PNG 得到 RGBA 后，在 C 侧双线性采样 + 边缘镜像缩放到屏幕尺寸。
- **NAPI 桥**（`curtain_napi.cpp`）：`init/setSource/press/release/shouldQuit/getPixels/screenSize`；
  像素缓冲以普通 ArrayBuffer 拷贝返回（external ArrayBuffer 在 ArkTS 侧与
  `image.createPixelMap` 不兼容，实测会导致 PixelMap 创建失败或进程崩溃）。
- **窗口即幕布**：窗口矩形始终等于幕布矩形。拖拽释放后对窗口执行
  `recover()`（若最大化）+ `moveWindowToAsync` + `resizeAsync`；窗口之外即桌面，
  天然实现"揭开区域可见 + 点击穿透"，等价于上游 `gtk_widget_input_shape_combine_region`。
- 资源：上游 `desktop/icons/curtain.png` 由配方在 `package()` 阶段注入
  `share/curtain/harmony/project/entry/src/main/resources/rawfile/curtain.png`
  （二进制资源不入补丁管线）；应用图标为 SVG（文本补丁）。

## 上游测试清点（N=0）

- `configure.ac` 无 `AM_TESTS` / `AC_CONFIG_TESTDIR` / 测试宏；
- 根、`src/`、`desktop/`、`docs/` 的 `Makefile.am` 无 `TESTS`、无 `check_PROGRAMS`、
  无自定义 `check:` 目标；
- 源码树无 `test/`、`tests/` 目录与测试源文件。

消费者侧以实测替代：包内 `bin/curtain_check` 覆盖几何与缩放 28 项断言
（四边揭开/回盖、最小尺寸、关闭热区、缩放正确性），另有 ELF/AArch64、NAPI 链接、
适配树与许可证检查，见 `test_package/`。

## 构建与本地验证（2026-09-15）

- 环境：OHOS SDK clang 15.0.4、CMake、Ninja；无 Conan 依赖。
- `conan-verify`：G0-G4 全部 PASS（G2 干净 `conan create` 成功，CTest 执行
  `curtain_check` 28/28 通过）。
- `test_package`：16/16 断言通过（含 `libcurtain.so` 的 `libace_napi.z.so` NEEDED 校验）。
- CI 门禁脚本（增量模式）：L0/L1/L1e/L2/L5 PASS；L4 的 `targets` 误匹配 `gets`
  为已知误报。
- 说明：本机验证使用设备 profile（`ohos-aarch64-device`）。仓库 CI profile 中的
  `/data/service/hnp/bin/clang` 是 CI worker 的工具链位置，本机不存在；
  未修改仓库基础设施，平台 CI 仍按其自带 profile 构建。

## 设备功能验证（2026-09-15，签名 HAP）

全部实测通过（HarmonyOS 6.1.0.117，3120x2080）：

- 全屏遮罩：启动后整屏被幕布覆盖（01-launch.jpeg）。
- 拖拽揭开：真实手指拖拽与 uinput 注入拖拽均有效；右缘揭开后窗口变为 (0,0,1700,2080)，
  纵向揭开变为 (0,500,1700,2080)（02-peel.jpeg / 02-peel-right.jpeg / 02b-peel-top.jpeg）。
- 点击穿透：点击露出区域时应用无触摸日志，点击由桌面/浏览器接收（03-click-through.jpeg）。
- 回盖：从幕布内向左拖过左边缘，窗口恢复为 (100,0,3020,2080)（04-recover.jpeg）。
- 关闭：点击幕布右上角 X，日志 quit requested，进程退出（05-close.jpeg）。
- 重启：再次启动后全屏遮罩与全部交互正常。

证据目录：`gui-adaptation-progress/curtain/device-verify/`（截图与 hilog 片段）。

## 已知限制

- `setWindowTopmost`（置顶）需要系统权限 `ohos.permission.WINDOW_TOPMOST`，实测返回
  201（Permission denied）。被点击拉起的其他窗口可能盖住幕布，需重新启动应用置前；
  核心遮罩/揭开/穿透行为不依赖该权限。
- 自由窗口状态下，幕布最顶部边缘可能被系统窗口热区/悬浮标题栏占用；最大化/全屏状态下
  X 点击实测正常。系统 Dock 始终绘制在幕布之上。
- 随包不发布 GTK/Broadway 版二进制：Broadway 只能在浏览器中显示，不能提供桌面遮罩，
  作为"适配完成"证据会产生误导；上游 GTK 源码仍随归档完整保留。

## 依赖版本

无 Conan 运行时/构建依赖；构建工具来自 OHOS SDK（clang 15.0.4、CMake）与仓库 CI 环境。

## 对话记录（适配过程摘要）

- 2026-09-15 接手 Curtain 0.3：核对交接文档与真机环境，确认 OHOS GTK 仅 Broadway、需原生适配。
- 建立独立 worktree（基于 main 68f967a78），官方归档 init-build；`.orig` 保持原样
  （哈希 382865145a78984c）。
- 新增 ArkUI 宿主工程与 C 核心（移植 `callbacks.c` 几何与 `utils.c` 缩放语义），上游源码零修改，
  补丁全部为新增文件。
- 真机无头测试 `curtain_check` 28/28；`conan-verify` G0-G4 PASS；`test_package` 16/16。
- 真机调试发现并修复：external ArrayBuffer 与 `image.createPixelMap` 不兼容（改为拷贝
  ArrayBuffer）；异步图片 API 释放顺序导致的崩溃；hilog `%f` 格式问题。
- 知识草稿 E429：新增文件补丁必须用 `--- /dev/null` 头；refresh-patch 的 dry-run 会在
  `.orig` 留下空文件并与 Conan patch_ng 冲突（本地流程已规避）。
- 真机功能验证完成：全屏遮罩、拖拽揭开、点击穿透、回盖、X 关闭、重启全部通过。

**编译结束**: 2026-09-15
**最终状态**: built（conan-verify G0-G4 PASS；本地 CI 门禁 PASS；真机功能验证通过；W4 独立审计 pass）
---

**编译结束**: 2026-09-15 16:26
**最终状态**: built
