# unshield

> 从 InstallShield CAB 文件中提取文件的命令行工具

## 简介

unshield 是一个用于提取 InstallShield Cabinet (.cab) 文件的工具和库，支持 InstallShield 版本 5 及以上。它包含一个命令行工具和 libunshield 库。

unshield 使用 C 语言编写，基于 CMake 构建系统。依赖 zlib 库进行解压缩，可选 OpenSSL 用于 MD5 校验（内建 MD5 实现可作为备选）。

## 输出

| 产物 | 类型 | 说明 |
|------|------|------|
| `unshield` | CLI | 主命令行工具（列出/提取 .cab 文件） |
| `unshield-deobfuscate` | CLI | 辅助工具 |
| `libunshield.so` | 共享库 | 用于提取 InstallShield CAB 文件的 C 库 |

## OHOS 适配要点

1. **CMake 原生构建**: unshield 使用标准 CMake 构建系统，无需特殊配置
2. **依赖**: 仅需 zlib，OpenSSL 为可选（内建 MD5 可用）
3. **静态/动态库**: 默认构建共享库（libunshield.so），非系统同名库，遵循默认动态链接策略
4. **ELF 签名**: 需 CI worker 对二进制进行 ELF 签名以确保可执行

## 依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| zlib | >= 1.x | 必需，用于 CAB 文件解压缩 |
| OpenSSL | 可选 | 用于 MD5 校验（内建 MD5 备选） |

## 功能验证

```bash
unshield --version   # 输出版本信息
unshield --help      # 输出帮助信息
unshield l file.cab  # 列出 CAB 文件内容
```

## 参考

- [上游仓库](https://github.com/twogood/unshield)
- [Savannah 发布页](https://download.savannah.nongnu.org/releases/unshield/)