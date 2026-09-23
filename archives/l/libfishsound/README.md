# libfishsound

libfishsound 提供统一的编程接口，用于在 Ogg 流中解码和编码 Vorbis 与 Speex
音频（由 CSIRO 澳大利亚 / annodex 项目开发，现属 Xiph.org 生态）。

## 功能概述

- 以 `FishSound*` 句柄封装 Vorbis 与 Speex 编解码器的细节差异
- 解码：`fish_sound_decode()` 喂入 Ogg 封装的压缩包，回调返回非交织/交织 float PCM
- 编码：`fish_sound_encode_float()` 喂入 PCM，回调返回压缩包，支持 flush
- 注释（元数据）读写：Vorbis comment / Speex string 统一 API
- 编解码器自动识别：`fish_sound_identify()`
- 帧号跟踪、交织模式切换、命令通道（`fish_sound_command()`）

## OHOS 适配

- Autotools 构建系统；config.guess/config.sub 通过补丁增加 HarmonyOS 识别
  （E007 模式），原生配置后在 `aarch64-unknown-linux-ohos` 三元组下编译
- 依赖由 Conan 制品仓提供：libogg（必需）、libvorbis、speex；
  头文件/库经 pkg-config 模块（PkgConfigDeps 生成）供 configure 检测
- FLAC 编解码支持当前禁用（`--disable-flac`）：制品仓 flac 配方固定
  libogg/1.3.5，与本包依赖 libogg/1.3.6 冲突（见 1.0.1 notes.md）
- 示例工具（fishsound-decode 等）依赖 liboggz/libsndfile，未适配时
  configure 自动跳过，不影响库本体

## 依赖关系

- 编译+运行：libogg、libvorbis、speex
- 可选（本包未启用）：flac（编解码）、liboggz/libsndfile（示例程序）

## 参考资料

- 官网：https://xiph.org/fishsound/
- 源码：https://downloads.xiph.org/releases/libfishsound/
