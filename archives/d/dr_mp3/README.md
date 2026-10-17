# dr_mp3

dr_mp3 是零依赖、单头文件的 MP3 音频解码库，以可移植 C89 编写，来自 dr_libs 单仓库（github.com/mackron/dr_libs）。支持 MPEG1/2 Layer III 解码为 f32/s16 PCM、VBR/CBR、ID3v2/ID3v1/XING/VBRI 标签解析与 seek 点计算。本归档适配的版本为 0.7.2。

## 功能概述

- **解码**：`drmp3dec_decode_frame` 低层单帧解码；高层 `drmp3_init_file` / `drmp3_init_memory` 流式解码
- **输出格式**：f32（`drmp3_read_pcm_frames_f32`）或 s16（`drmp3_read_pcm_frames_s16`）
- **元数据**：ID3v1 / ID3v2 / APE / XING / VBRI 解析回调（`drmp3_meta_proc`）
- **Seek**：`drmp3_calculate_seek_points` + `drmp3_seek_to_pcm_frame`

## OHOS 适配

- 库为 **header-only**（单文件 `dr_mp3.h`，`#define DR_MP3_IMPLEMENTATION` 后实现编译进消费者），无编译产物、无链接依赖，纯可移植 C89、无平台分支代码，OHOS 无需补丁
- 包内仅交付 `include/dr_mp3.h` 与 `licenses/LICENSE`；tarball 中的 dr_wav.h / dr_flac.h 归属各自包（dr_wav / dr_flac），不混入本包
- 上游 CMake 测试套件（tests/mp3/mp3_basic 等）依赖 `tests/testvectors` 数据集，官方 tarball 不含（仅 .gitkeep）；test_package 以源内真实 MPEG1 Layer III 帧（128 kbps / 44.1 kHz / 立体声，417 字节）解码测试覆盖功能验证（11 断言）

## 依赖关系

- 编译/运行依赖：无（零依赖库）
- 系统依赖：无

## 参考资料

- 官方仓库: https://github.com/mackron/dr_libs
- 本版本 tag: `mp3-0.7.2`（commit 547c211a87a06a42bf62c1366616aa14b57dd429）
- 源码 tarball sha256: `fd94a133e5753007e584bc0ab4747d7db3b26f210154f80ee2b44137286cd659`
