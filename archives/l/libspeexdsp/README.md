# libspeexdsp — Xiph Speex DSP 处理库

- 上游：https://speex.org/（重采样/AEC 回声消除/降噪/AGC/Jitter buffer）
- 包名说明：libspeexdsp 与既有归档 speexdsp/* 为不同包名并存（同 vorbis/libvorbis、
  ogg/libogg、libopus/opus 先例；Debian 命名 libspeexdsp1）
- 构建系统：Autotools（xiph 官方 tarball，新式 config 脚本三补丁）
- 验证：test_package 重采样 API 真调用；上游 5 个 BUILD_EXAMPLES 测试程序本地全跑
