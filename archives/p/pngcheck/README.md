# pngcheck

PNG/JNG/MNG 文件检查和信息打印工具。

## 概述

pngcheck 是一个用于验证 PNG、JNG 和 MNG 文件完整性的命令行工具，同时可打印文件的详细信息（尺寸、类型、压缩率等）。它能检测文件中的各种错误，包括损坏的 chunk、缺失的 IEND、截断文件等。

## 版本信息

| 版本 | 状态 | 日期 | 备注 |
|------|------|------|------|
| 4.0.1 | built | 2026-05-25 | cmake 编译，zlib 静态链接 |

## 编译配置

- **构建系统**: cmake
- **编译器**: clang 15.0.4
- **依赖**: zlib 1.3.1（预编译包，静态链接）
- **configure选项**: `-DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX -DPNGCHECK_USE_SYSTEM_ZLIB=ON`

## 使用说明

```bash
# 检查单个PNG文件
pngcheck file.png

# 详细模式
pngcheck -v file.png

# 安静模式（仅输出错误）
pngcheck -q file.png

# 搜索PNG片段
pngcheck -s mixed_file.bin
```

注意：pngcheck 不支持 `--version` 参数，版本信息通过直接运行 `pngcheck` 获取。

## 许可证

HPND (Historical Permission Notice and Disclaimer)