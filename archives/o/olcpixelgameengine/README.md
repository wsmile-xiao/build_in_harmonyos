# olcpixelgameengine

单头文件 C++17 游戏引擎（OneLoneCoder），OLC-3 许可。

## 功能概述

- 单头文件 `olcPixelGameEngine.h`：像素级 2D/3D 游戏引擎与绘图 API
  （Sprite、Decal、着色器、QuickGUI 等），扩展头 `extensions/olcPGEX_*.h`
  与工具头 `utilities/olcUTIL_*.h` 一并随包导出
- 上游仓库：https://github.com/OneLoneCoder/olcPixelGameEngine

## OHOS 适配

- 按 header-only 打包（`package_type=header-library`），无构建系统、无第三方依赖
- OHOS 无上游原生窗口后端（Win32/X11/GLUT/Emscripten 均不适用）：消费方以
  上游原生无头模式 `-DOLC_PGE_HEADLESS` 编译使用（Platform_Headless/
  Renderer_Headless 为上游实现，非空壳），已在 OHOS aarch64 实测可编译、
  可链接、可运行（test_package 消费者用例 + test_ohos 鸿蒙专项测试）
- 详见 `archives/o/olcpixelgameengine/2.30/notes.md` 与知识草稿
  `knowledge/drafts/DRAFT-olcpixelgameengine-2.30-olc-pge-headless-mode.{kv,md}`

## 依赖

无（header-only，零 requires）

## 参考资料

- 官方仓库：https://github.com/OneLoneCoder/olcPixelGameEngine
- OLC-3 许可证：https://github.com/OneLoneCoder/olcPixelGameEngine/blob/master/LICENCE.md
