# Julius

julius 是 Caesar III（凯撒大帝3）的开源重制版游戏（bvschaik/julius），纯 C 实现，
CMake 构建，AGPL-3.0 许可证。

## 功能概述

- 完整复刻 Caesar III 游戏逻辑（城市规划、模拟、战役/沙盒）
- SDL2 图形渲染 + SDL_mixer 音频输出
- 36 个 CTest 集成测试（autopilot savegame 语义比较）

## OHOS 适配

- E092：CMake 不识别 HarmonyOS，`CMAKE_SYSTEM_NAME=Linux` + `CMAKE_SYSTEM_PROCESSOR=aarch64`
- CMake 4.x：`CMAKE_POLICY_VERSION_MINIMUM=3.5`
- 依赖通过模块模式 Find 注入 cache 变量（SDL2_INCLUDE_DIR/SDL2_LIBRARY/SDL2_MIXER_INCLUDE_DIR/SDL2_MIXER_LIBRARY）
- 构建 `--parallel 1` 规避 HMDFS mkfifo 坑
- `bin/julius` 用 binary-sign-tool 自签（OHOS ELF 必需）
- 无音频输入；测试用 stub 音视频，无需真实音频/显示设备

- **验证边界（R40）**：官方 CI 在 OHOS 上通过 36/36 CTest 集成测试（上游 test/stub 桩件 + autopilot 存档语义比较）与 test_package CLI 断言（--help / 非法参数）。**SDL2 图形渲染/游戏主循环在 OHOS 上的实际运行未验证**——CI 环境无显示/图形栈，测试仅覆盖 SDL 初始化之前的参数解析路径与桩件集成逻辑。
- **建议**：在带显示/图形栈的 OHOS 环境人工确认适配完整性（实际启动游戏，验证渲染与音频输出）。

## 依赖关系

- 构建/运行依赖：sdl2/2.30.10、sdl2_mixer/2.8.1（已发布到 ohpcd）
- 可选：libpng（无系统 libpng 时回退捆绑 ext/png + ext/zlib）
- 运行时还需 Caesar III 原版数据目录（与包本身无关，非构建依赖）

## 参考资料

- 上游仓库：https://github.com/bvschaik/julius
- 上游构建文档：doc/BUILDING.md
