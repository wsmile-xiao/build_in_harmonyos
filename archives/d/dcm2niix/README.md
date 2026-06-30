# dcm2niix

DICOM 到 NIfTI 格式转换器 — 将医学影像文件从 DICOM 格式转换为 NIfTI 格式。

- **主页**: https://github.com/rordenlab/dcm2niix
- **许可证**: BSD-3-Clause
- **构建系统**: CMake（SuperBuild + ExternalProject_Add）
- **功能**: 识别 DICOM 系列、合并切片为 3D volume、生成 NIfTI 文件和 BIDS JSON 侧边文件
- **支持格式**: MR/CT/PET 等多种医学影像模态