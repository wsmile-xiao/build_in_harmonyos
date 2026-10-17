# nestopia-ue

Nestopia UE（Undead Edition）——NES/Famicom 模拟器，Nestopia 的社区维护 fork。

## 简介
- 超过 200 个 mapper 板卡支持的精确 NES 模拟核心（CPU/PPU/APU）
- JG API 绑定层（libretro 之外的独立前端接口）
- 上游提供 Linux（FLTK GUI）/Windows（DirectX）两前端

## OHOS 适配（1.53.2）
- **裁剪**：FLTK GUI 前端（fltkui/videomanager/uiadapter）——FLTK 未发布且 OHOS 无桌面 GL 栈
- **保留**：模拟核心（source/core）、JG 绑定（jg.cpp）、manager 层（jgmanager/setmanager/chtmanager/logdriver 等）
- **新增**：headless 驱动（--version / --frames N），CLI 驱动核心帧循环
- **依赖**：sdl2/2.32.10（manager 层）、zlib/1.3.1（状态压缩）、libsamplerate/0.2.2（音频重采样）
- **用法**：`nestopia --frames 120 game.nes`（NstDatabase.xml 从安装的 share/nestopia/ 或 $PWD 查找）

## 依赖
- sdl2 2.32.10
- zlib 1.3.1
- libsamplerate 0.2.2
