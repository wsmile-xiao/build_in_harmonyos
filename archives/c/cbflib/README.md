# cbflib（CBFlib）

CBF/imgCIF 晶体学二进制文件库（Crystallographic Binary File library）：
- `libcbf` — CBF/imgCIF 读写核心（支持 canonical/packed/byte_offset 等压缩编码与 MD5 摘要）
- `libimg` — 衍射图像（mar/adsc 等）读取辅助库
- 工具集 — `cif2cbf`、`img2cif`、`makecbf`、`convert_image`、`convert_minicbf`、
  `cbf2nexus`/`nexus2cbf`/`minicbf2nexus`（HDF5/NeXus 往返）等

上游：https://github.com/yayahjb/cbflib （SourceForge 项目 cbflib 同步发布）
许可证：GPL-2.0-or-later OR LGPL-2.1-or-later（包整体 GPL，API 可选 LGPL）

## OHOS 适配

- 版本级 manifest/notes：见 `0.9.7/`
- 核心依赖：hdf5/1.14.6、pcre/8.45（zlib/libaec 经 hdf5 传递）
- 上游 Makefile 的可选外部组件（本地 hdf5/pcre/tiff/PyCifRW 下载构建）经上游
  合法开关裁剪；无平台条件编译补丁
