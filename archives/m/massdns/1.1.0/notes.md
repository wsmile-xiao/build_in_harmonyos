# massdns 1.1.0 适配笔记

## 编译环境
- 构建系统: makefile（纯 Makefile，无 configure，无 make install）
- 编译日期: 2026-07-16
- 编译器: clang 15.0.4
- 状态: built

## 软件概述

MassDNS 是高性能 DNS stub resolver，针对需要解析大量域名（百万甚至十亿级）的场景。
使用自定义 DNS 实现（自 v0.3 起不再依赖 ldns），基于 Linux epoll 机制实现高并发。

## 编译步骤

1. 源码下载：从 GitHub 下载 v1.1.0 tag 的 tar.gz
2. 编译：
   ```bash
   make CC=clang PROJECT_FLAGS='-DMASSDNS_REVISION="1.1.0"' -j1
   ```
3. 手动安装（Makefile 有 install 目标但使用 GNU coreutils install，鸿蒙可能无此命令）：
   ```bash
   mkdir -p $PACKAGE/bin $PACKAGE/share/man/man1
   cp bin/massdns $PACKAGE/bin/
   cp doc/massdns.1 $PACKAGE/share/man/man1/
   ```
4. ELF 签名（鸿蒙必需）：
   ```bash
   binary-sign-tool sign -inFile massdns -outFile massdns.signed -selfSign 1
   ```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | git describe 失败 | tarball 无 .git 目录，Makefile 中 `PROJECT_FLAGS=-DMASSDNS_REVISION=\"$(shell git describe --tags --dirty=+)\"` 失败 | 在 make 命令中显式传递 `PROJECT_FLAGS='-DMASSDNS_REVISION="1.1.0"'` |
| 2 | CC 默认为 cc | Makefile 使用 `$(CC)`，未设置时默认为 cc，CI worker 上可能无 cc | 通过 `self.conf.get("tools.build:compiler_executables:c")` 从 Conan 获取编译器，显式传递 `CC=clang`（R33） |
| 3 | make install 依赖 GNU install | Makefile install 目标使用 `install -m` 命令，鸿蒙无 GNU coreutils install | conanfile.py 使用 Conan 的 `copy()` 函数手动复制文件，不依赖 make install |
| 4 | ELF 签名 | 鸿蒙要求 ELF 二进制必须签名才能执行 | 在 package() 中使用 binary-sign-tool 签名（R38/E082） |

## 源码修改

无补丁，源码无需修改。所有适配通过 Conan 配方的 build() 和 package() 方法完成。

## 依赖说明

无外部依赖。massdns 自 v0.3 起使用自定义 DNS 实现，不再依赖 ldns。

## 构建系统说明

massdns 使用纯 Makefile 构建：
- `all` 目标：编译 `src/main.c` 到 `bin/massdns`，使用 `-DHAVE_EPOLL -DHAVE_SYSINFO`（Linux 特定）
- `nolinux` 目标：不使用 epoll/sysinfo 的版本（用于非 Linux 平台）
- HarmonyOS 基于 Linux 内核，支持 epoll 和 sysinfo，使用 `all` 目标即可
- `install` 目标：使用 GNU `install` 命令，鸿蒙可能无此命令

## 版本验证

```bash
$ massdns --version
massdns
```

## 功能验证

```bash
$ massdns --help
Usage: massdns [options] [domainlist]
  -b  --bindto           Bind to IP address and port. (Default: 0.0.0.0:0)
  -c  --resolve-count    Number of resolves for a name before giving up. (Default: 50)
  ...
```

## 交付物

| 文件 | 说明 |
|------|------|
| massdns/1.1.0/conanfile.py | Conan 配方（Makefile 构建 + ELF 签名） |
| massdns/1.1.0/conandata.yml | 源码 URL + sha256 |
| massdns/1.1.0/test_package/ | 测试包（--version + --help 烟雾测试） |
| massdns/commands.json | 命令行工具声明（R38） |

## 注意事项

- massdns 是 Linux 特定工具（使用 epoll），HarmonyOS 基于 Linux 内核支持
- 无 configure 脚本，直接 make 编译
- 构建产物为单一二进制 `bin/massdns`
- Makefile 的 install 目标使用 GNU install 命令，conanfile.py 改用 Conan copy() 函数
- 需要手动传递 PROJECT_FLAGS 以避免 git describe 失败
- massdns --version 输出 "massdns"，可能返回非零退出码，test.sh 验证输出内容而非退出码
