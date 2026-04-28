# DAR (Disk ARchive)

DAR 是一个全功能的磁盘归档工具，支持压缩（gzip、bzip2、xz、lzo、zstd）、加密、增量备份、分卷等功能。

## 功能概述
- 全量/增量/差异备份
- 支持多种压缩算法（gzip, bzip2, xz, lzo, zstd）
- AES 加密支持
- 分卷归档（可跨越多个存储介质）
- 文件排除/包含过滤
- 网络操作（通过 dar_slave/dar_xform）

## OHOS 适配
- 需要更新 config.guess/config.sub 以识别 HarmonyOS 平台
- po/Makefile.in 需要调整以兼容交叉编译环境
- 多个源文件涉及平台特定 API（check-*.cpp 系列文件）需要适配
- 实际编译使用了 15 个补丁

## 依赖关系
- **编译依赖**: zlib, bzip2, openssl, libarchive (可选)
- **运行依赖**: zlib, bzip2, openssl

## 参考资料
- 官网: https://dar.sourceforge.net/
- 源码: https://sourceforge.net/projects/dar/
