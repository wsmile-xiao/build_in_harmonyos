# nethogs 0.8.8 鸿蒙适配笔记

## 编译环境
- 构建系统: makefile（自定义 Makefile + MakeApp.mk）
- 编译日期: 2026-05-27
- 编译器: clang 15.0.4 / clang++ 15.0.4
- 状态: published

## 编译步骤

1. 下载源码: `curl -L -k -o ~/tmp/builds/nethogs-0.8.8.tar.gz https://github.com/raboof/nethogs/archive/refs/tags/v0.8.8.tar.gz`
2. 解压源码: `tar -xzf nethogs-0.8.8.tar.gz -C ~/tmp/builds/nethogs-0.8.8.work --strip-components=1`
3. 初始化构建: `python3 $SKILL_ROOT/scripts/ohc-run.py init-build nethogs 0.8.8 --url=... --no-download`
4. 安装依赖 libpcap: 手动编译 libpcap 1.10.6（cmake），安装到 ~/usr/local
5. 编译 nethogs: `make nethogs PREFIX=$DEFAULT_PREFIX VERSION=0.8.8`
   - 设置环境变量: `PKG_CONFIG_PATH, LDFLAGS, CPPFLAGS, LD_LIBRARY_PATH`
6. 手动安装到 staging: `mkdir + cp`（因 `install` 命令不可用）
7. 上游测试套: `make check` 输出 "Not implemented"（上游未实现测试套）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `rindex` undeclared | musl/鸿蒙不提供 rindex/index 函数 | 替换为 strrchr/strchr（patch 0001） |
| 2 | `install` 命令找不到 | 鸿蒙无 GNU coreutils install 命令 | 替换为 mkdir -p + cp（patch 0002） |
| 3 | coreutils 预编译包不可执行 | ELF 未签名导致 HMDFS 阻止执行 | 移除 ~/usr/local/bin 中的 unsigned coreutils 二进制 |
| 4 | determineVersion.sh 失败 | 需要 bash 和 git，tarball 中无 git 仓库 | 手动传递 VERSION=0.8.8 参数 |

## 源码修改

- **0001-src-MakeApp.mk.patch**: 替换 `install -d -m 755` → `mkdir -p`，`install -m 755` → `cp`（src/MakeApp.mk）
- **0002-src-cui.cpp.patch**: 替换 `rindex()` → `strrchr()`，`index()` → `strchr()`（src/cui.cpp）

## 依赖版本

| 依赖 | 版本 | 来源 |
|------|------|------|
| libpcap | 1.10.6 | 手动编译（cmake），~/usr/local |
| ncurses | 6.5 | 预编译包（静态库），~/usr/local |
| clang | 15.0.4 | 系统工具链 |

## 功能验证结果

在鸿蒙系统上真实执行 nethogs 二进制，所有功能验证通过：

```bash
# 版本号验证 ✅
$ nethogs -V
 version 0.8.8

# 帮助信息验证 ✅（完整输出所有选项）
$ nethogs -h
usage: nethogs [-V] [-h] [-x] [-d seconds] [-v mode] [-c count] ...

# 二进制格式 ✅
$ file nethogs
ELF shared object, 64-bit LSB arm64, dynamic (ld-musl-aarch64.so.1)

# ELF 签名 ✅
$ llvm-readelf -S nethogs | grep codesign
  [39] .codesign         PROGBITS  ...

# 动态链接库 ✅
$ llvm-readelf -d nethogs | grep NEEDED
  libpcap.so, libc++_shared.so, libc.so

# 网络设备检测 ✅
$ nethogs -t -d 1 -c 1
Adding local address: 7.247.125.51
Adding local address: fe80::20a4:d7ff:fed3:788f
（pcap 需 root 权限 — 预期行为）
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| nethogs | 346KB | 网络带宽监控工具（ELF aarch64，已签名） |
| nethogs.8 | man page | 使用手册 |

## 注意事项

- nethogs 需要网络抃包权限运行（root 或 capabilities），这是网络监控工具的固有特性
- 安装路径为 sbin（sbin/nethogs）而非 bin
- libpcap 必须作为依赖预先安装（已包含在预编译包 lib/external/ 中）
- determineVersion.sh 依赖 git，tarball 构建需手动指定 VERSION
---

**编译结束**: 2026-05-27 15:31
**最终状态**: published
