# dr_libs

dr_libs 是 mackron（David Reid）维护的单头音频解码库集合（github.com/mackron/dr_libs），一个仓库同时交付三个互相独立的零依赖单头库：dr_wav（WAV 读写）、dr_flac（FLAC 解码）、dr_mp3（MP3 解码）。本归档适配的版本为 0.0-git.dfe8377（master 快照 dfe8377，含 dr_wav 0.14.6 / dr_flac 0.13.4 / dr_mp3 0.7.4 三头）。

## 功能概述

- **dr_wav**：WAV 读写（RIFF/W64 容器，PCM/f32/s32/s16 转换读写，`drwav_init_memory_write` 内存写）
- **dr_flac**：FLAC 解码（native FLAC + Ogg FLAC，f32/s32/s16 输出，seek 表计算）
- **dr_mp3**：MP3 解码（MPEG1/2 Layer III，f32/s16 输出，ID3/XING/VBRI 元数据）
- 每个头独立使用：消费者在恰好一个翻译单元定义 `DR_WAV_IMPLEMENTATION` / `DR_FLAC_IMPLEMENTATION` / `DR_MP3_IMPLEMENTATION` 即可把实现编译进自身

## OHOS 适配

- 库为 **header-only** 三合一聚合包（三头各自独立，无交叉 include、无符号冲突），无编译产物、无链接依赖，纯可移植 C89/C99、无平台分支代码，OHOS 无需补丁
- 包内交付 `include/dr_wav.h`、`include/dr_flac.h`、`include/dr_mp3.h` 与 `licenses/LICENSE`
- 同仓已有按单头拆分的兄弟包（dr_wav 0.13.17 / drwav 0.14.5 / dr_flac 0.12.39 / dr_mp3 0.7.2，各自只交付单头）；本包为需要整套 dr_libs 的消费者提供一次依赖三头全量入口（包名精确查重已过）
- 上游 tests/ 依赖 git submodule testvectors 数据集，官方 tarball 不含数据文件；test_package 以同一翻译单元三头共存编译 + dr_wav 内存写读往返断言覆盖功能验证（17 断言）

## 依赖关系

- 编译/运行依赖：无（零依赖库）
