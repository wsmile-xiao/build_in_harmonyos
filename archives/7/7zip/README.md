# 7-Zip

## 简介

7-Zip 是一款高压缩比的文件归档工具，支持 7z、ZIP、GZIP、BZIP2、TAR 等多种格式。它使用 LZMA/LZMA2 压缩算法，压缩率优于多数同类工具。

## OHOS 适配

- 7zip 使用自定义 Makefile 构建系统，不支持标准的 configure/make install 流程
- 需在 CXXFLAGS 中添加 `--target=aarch64-linux-ohos` 交叉编译参数
- 25.01 版本引入了 Rust 代码，需要通过 `DISABLE_RUST=1` 禁用或安装 Rust 工具链
- 安装阶段需手动复制二进制文件到目标目录

## 依赖

无外部编译依赖（自包含构建）。

## 功能验证

```bash
7z --help
echo "test" > test.txt && 7z a test.7z test.txt && 7z l test.7z
```

## 参考

- 官网: https://www.7-zip.org
- 源码: https://www.7-zip.org/download.html
