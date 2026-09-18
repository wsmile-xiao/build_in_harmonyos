# lgeneral

LGeneral 是 Panzer General 风格的回合制策略游戏（SDL 1.2 图形界面，C 语言），
上游为 sourceforge.net/projects/lgeneral。本归档收录其 OHOS (HarmonyOS PC,
aarch64) 适配。

## 功能概述

- `lgeneral` — 游戏主程序：回合制战争模拟（地图、单位、战役剧本）
- `lgc-pg` — Panzer General 原版数据转换器（需原版 PG 数据）
- `lged` — 关卡/剧本编辑器（终端工具，无图形依赖）
- `ltrextract` — LTX 资源包提取器

游戏本体数据（地图/单位/剧本）不随源码分发：需用 `lgc-pg` 从 Panzer
General 原版安装介质转换，或使用社区制作的战役包。

## 图形/音频栈

SDL 1.2 API 由 sdl12-compat（SDL2 后端）满足；音频经 SDL_mixer 符号
（sdl2_mixer 静态库提供）。无头环境验证用 `SDL_VIDEODRIVER=dummy
SDL_AUDIODRIVER=dummy`。

## 版本

| 版本 | 说明 |
|------|------|
| 1.4.4 | 上游 2021 年最终版；OHOS 适配见 [1.4.4/notes.md](1.4.4/notes.md) |
