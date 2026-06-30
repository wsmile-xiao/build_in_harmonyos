# pdf2image 1.17.0 编译笔记

2026-05-27

## 编译流程

 pdf2image 是纯 Python 包（pip 安装方式），不是传统的 autotools/cmake 项目。

  - 使用 `python3 -m pip install pdf2image==1.17.0 --prefix=$DEFAULT_PREFIX` 安装到 staging 目录
  - 依赖 poppler-utils 提供的 pdftoppm 二进制工具  - 依赖 Pillow 提供图像处理功能  ## 关键发现
 1. **HMDFS 权限问题**: .so 文件 (Pillow _imaging*.so) 创建时 umask=022，但 pip 安装时文件权限为 770，导致 "Permission denied" 错误， 解决方法: 使用 `cp` 而不是 `cp --no-preserve=mode` (zsh 不支持此选项).  2. **pdftoppm RPATH**: pdftoppm 二进制有 RPATH `../lib/` 指向 libpoppler.so，在扁平 tar.gz 结构中正确（bin/ 和 lib/ 相邻）.  3. **pip 安装方式**: pdf2image 通过 pip 直接安装，不需要 configure/make/make install 流程.  4. **打包**: 由于是 pip 包，打包时需要将 pdf2image Python 文件、Pillow Python 文件和 .so、poppler 二进制和共享库一起打包.  ## 制品文件:
  packaging/pdf2image-1.17.0-ohos-aarch64.tar.gz - 74MB - packaging/pdf2image-1.17.0-ohos-aarch64-debug.tar.gz - 74MB  - 包含: bin/ (poppler 工具), lib/python3.12/site-packages/pdf2image/, lib/python3.12/site-packages/PIL/, lib/*.so, lib/libpoppler.so* 
## 依赖说明:  pdf2image 本身是纯 Python 包，但运行依赖 Pillow（图像处理）和 poppler-utils（pdftoppm 二进制）。打包时将所有依赖一起打包以确保用户安装后可直接使用。  ## 已知限制:  - HMDFS 上 .so 文件权限问题导致无法直接加载（需 umask 022）  - pdftoppm 有相对 RPATH，在扁平结构中可正常工作  - 纯 Python 包无 __version__ 属性，通过 PKG-INFO 确认版本为 1.17.0  EOF