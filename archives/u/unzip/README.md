# unzip

Info-ZIP 的解压缩工具，用于提取 ZIP 格式压缩文件。

## 版本
- 6.0 (当前)

## 功能
- 解压 ZIP 文件
- 支持大文件 (ZIP64)
- 支持 UTF-8 文件名
- 支持加密 ZIP 文件
- 包含 zipinfo, funzip, unzipsfx, zipgrep 工具

## 依赖
无外部依赖，纯 C 实现。

## 构建
```bash
make -f unix/Makefile generic CC=clang
```

## 许可证
Info-ZIP License
