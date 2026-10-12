# srf

SRF (Sequence Read Format) — DNA 测序数据容器格式的 C++ 实现，
基于 io_lib（libstaden-read）的 ZTR/SRF API。静态库 libsrf.a +
4 个 SRF 写读工具（testWrite/testRead/testWriteFastaq/testWriteSFF）。

- 上游: http://srf.sourceforge.net/（源码经 Debian 官方池镜像分发）
- 许可证: GPL-2.0-or-later
- 构建系统: autotools（2008 年代 maintainer-mode）
- 依赖: io_lib（libstaden-read）

## 适配版本

- 0.1: 已适配（上游 0.1+dfsg，conan create 全绿，见 0.1/notes.md）
