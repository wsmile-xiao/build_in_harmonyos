# libopus — Xiph Opus 音频编解码库

- 上游：https://opus-codec.org/（IETF RFC 6716 标准 Audio Codec）
- 包名说明：libopus 与既有归档 opus/* 为不同包名并存（同 vorbis/libvorbis、ogg/libogg
  先例；上游 pkg-config/Debian 命名习惯即 libopus）
- 构建系统：CMake
- 验证：test_package dlopen 探针 + 48kHz 立体声 encode/decode 真实回环
