# KiCad Footprint Libraries

KiCad 官方 footprint 资源库的 Conan 归档，提供 PCB 封装图形和焊盘定义数据。

主要内容：

- 155 个 KiCad `.pretty` footprint 库目录；
- 15435 个 `.kicad_mod` footprint 文件；
- KiCad 10 的 `fp-lib-table` 模板表。

OHOS 适配：这是平台无关的纯资源包，不编译 C/C++ 库或可执行文件；资源安装到 `share/kicad/footprints`，库表安装到 `share/kicad/template`，并通过 `KICAD10_FOOTPRINT_DIR` 导出资源位置。没有 Conan 编译/运行时依赖，源码许可证为 CC-BY-SA-4.0。

- Homepage: https://gitlab.com/kicad/libraries/kicad-footprints
- License: CC-BY-SA-4.0
- Package type: resource/data (`unknown`)
- Conan reference: `k/kicad-footprints/10.0.4`
