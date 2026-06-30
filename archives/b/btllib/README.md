# btllib

## 简介

btllib (Birol Lab Library) 是一个用于生物信息学应用的 C++ 库，提供了序列处理、哈希算法、Bloom过滤器等工具。

## 主要功能

- 序列读写（支持 FASTA、FASTQ、SAM 格式）
- Bloom 过滤器实现
- 哈希算法（nthash、aahash）
- 序列处理工具（indexlr、randseq、mi_bf_generate）

## 编译版本

- 1.7.8 (2026-06-16)

## 编译说明

btllib 使用 meson 构建系统，依赖 OpenMP。在鸿蒙系统上编译时需要注意：

1. 所有子项目的 CMakeLists.txt 需要修改 CMake 版本要求（从 < 3.5 改为 3.5...4.1）
2. 所有 bash 脚本需要修改 shebang（从 /bin/bash 改为 #!/usr/bin/env bash）
3. 测试需要 samtools，如果没有可以禁用测试目录

## 使用方法

安装后可以使用以下工具：

```bash
# 序列索引
indexlr --version

# 随机序列生成
randseq --help

# Bloom过滤器生成
mi_bf_generate --help
```

## 许可证

MIT License

## 官方网站

https://github.com/BirolLab/btllib