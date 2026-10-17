# zBoy

zBoy 是一个使用 SDL2 的 Game Boy 模拟器，可在桌面上加载并运行 Game Boy ROM。

## 功能

- 运行 `.gb`/`.gbc` 游戏 ROM。
- 通过 SDL2 提供窗口、图像渲染、键盘/手柄输入与可选音频。
- 支持存档、截图、缩放和多玩家网络连接。

## HarmonyOS 适配

配方沿用上游 SDL2 驱动，通过 Conan 注入 SDL2 编译和静态链接参数。HarmonyOS ARM64 真机测试覆盖 SDL 初始化、窗口创建、Renderer、RGB565 纹理更新与呈现；版本级笔记记录真机测试 ROM 结果及设备限制。

## 依赖

- 编译与运行：`sdl2/2.30.10`
- C 编译器与 Make

## 参考资料

- [zBoy SourceForge 项目与源码](https://sourceforge.net/projects/zboy/)
- [zBoy 0.71 文件目录](https://sourceforge.net/projects/zboy/files/)
