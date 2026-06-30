# grepcidr

## 软件简介

grepcidr 是一个用于过滤匹配 IPv4/IPv6 CIDR/网络规范的 IP 地址的命令行工具。它可以过滤标准输入中的 IP 地址，只输出匹配指定 CIDR 块的地址。

## 版本信息

- 当前版本: 2.0
- 许可证: GPL-2.0-or-later
- 官方网站: https://www.pc-tools.net/unix/grepcidr/

## 功能特性

- 支持 IPv4 和 IPv6 地址过滤
- 支持 CIDR 表示法 (例如: 192.168.1.0/24)
- 支持从文件或标准输入读取
- 支持反向匹配 (-v 选项)
- 支持大小写不敏感匹配 (-i 选项)

## 编译版本

| 版本 | 状态 | 编译日期 | 构建系统 |
|------|------|---------|---------|
| 2.0 | ✅ published | 2026-06-06 | makefile |

## 安装使用

### 从预编译包安装

```bash
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- grepcidr 2.0
```

### 使用示例

```bash
# 显示版本
grepcidr -V

# 过滤匹配 CIDR 的 IP
echo "192.168.1.100" | grepcidr "192.168.1.0/24"

# 从文件过滤
grepcidr "10.0.0.0/8" iplist.txt

# 反向匹配（输出不匹配的 IP）
cat iplist.txt | grepcidr -v "192.168.0.0/16"
```

## 依赖说明

- 无外部依赖（单文件 C 程序）
- 编译器: clang 15.0.4

## 编译说明

grepcidr 使用简单的 Makefile 构建，无需 configure 步骤：

```bash
make PREFIX=/path/to/install CFLAGS="-fPIC -O2 -Wall -Werror"
make install PREFIX=/path/to/install
```

## 注意事项

- 版本选项为 `-V` 而非 `--version`
- 支持 DESTDIR 模式进行 staging 安装

## 更多信息

- 完整编译笔记: [2.0/notes.md](./2.0/notes.md)
- 编译元数据: [2.0/manifest.yaml](./2.0/manifest.yaml)