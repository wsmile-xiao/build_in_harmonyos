# vorbis 1.3.7 Conan 配方摘要

- 包名线说明：`vorbis`（平台任务 #13473）——与既有 `libvorbis/1.3.7`（archives/l/libvorbis/）同源码不同包名线，多包名先例同 ogg/libogg；两者并存互不冲突
- 构建系统：CMake（上游自带 CMakeLists.txt，避开 Autotools config.status 临时目录权限问题）
- 上游源码：https://downloads.xiph.org/releases/vorbis/libvorbis-1.3.7.tar.gz（与 libvorbis 线同一官方 tarball，sha256 相同）
- 依赖：`ogg/1.1.1`（旧 ogg 包名线，archives/o/ogg/，PR #10038）
- Conan 组件：
  - `Vorbis::vorbis`
  - `Vorbis::vorbisenc`
  - `Vorbis::vorbisfile`
- 验证：非交互 `test_package` 覆盖版本字符串、编码初始化、comment API 与 vorbisfile 符号链接；上游 `test/test.c` 往返矩阵（1-8 声道 × 11 质量档 × 6 采样率 = 528 组合）在安装包上全量通过
