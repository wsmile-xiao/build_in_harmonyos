# umoci

umoci: Umoci Modifies Open Containers' Images — OCI 容器镜像操作工具。

## 描述

umoci 是一个 Go 语言编写的 OCI 容器镜像操作工具，支持解包、打包、修改等操作。

## 编译版本

- 0.6.0 (built)

## 编译说明

由于 Go linker 在 HarmonyOS 平台存在 file-backed mmap RWX 限制（见 E105），Go 项目无法直接编译。
umoci 使用官方预编译 arm64 二进制 + ELF 签名的方式部署。

## 参考

- 官方仓库: https://github.com/opencontainers/umoci
- 编译限制详见: archives/u/umoci/0.6.0/notes.md
