# KiCad 3D Model Libraries

KiCad 官方 3D 模型资源库的 Conan 归档，提供 PCB 元器件的三维模型数据。

主要内容：

- 105 个 KiCad `.3dshapes` 模型库目录；
- 7245 个 `.step`（ISO-10303-21）模型文件；
- KiCad 10 已移除 VRML 模型，本库仅含 STEP 模型。

OHOS 适配：这是平台无关的纯资源包，不编译 C/C++ 库或可执行文件；资源安装到 `share/kicad/3dmodels`，并通过 `KICAD10_3DMODEL_DIR` 导出资源位置。没有 Conan 编译/运行时依赖，源码许可证为 CC-BY-SA-4.0。

- Homepage: https://gitlab.com/kicad/libraries/kicad-packages3D
- License: CC-BY-SA-4.0
- Package type: resource/data (`unknown`)
- Conan reference: `k/kicad-library/3d-10.0.5`
