# libvorbis 1.3.7 Conan 配方摘要

- 构建系统：CMake
- 上游源码：https://downloads.xiph.org/releases/vorbis/libvorbis-1.3.7.tar.gz
- 依赖：`libogg/1.3.6`
- Conan 组件：
  - `Vorbis::vorbis`
  - `Vorbis::vorbisenc`
  - `Vorbis::vorbisfile`
- 验证：非交互 `test_package` 覆盖版本字符串、编码初始化、comment API 与 vorbisfile 符号链接。
