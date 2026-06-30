# Chez Scheme 10.3.0 — aarch64 预编译包

## 概述

Chez Scheme 10.3.0 的 aarch64 预编译包，使用 portable bytecode (pb) 架构构建。
适用于不支持硬链接的文件系统和无 ncurses/x11 的嵌入式/鸿蒙平台。

## 编译配置

| 参数 | 值 |
|------|------|
| 机器类型 | tpb64l (threaded pb 64-bit little-endian) |
| 平台标记 | tunknown |
| 编译器 | clang |
| 配置选项 | `--pbarch --disable-curses --disable-x11 --as-is` |
| 架构 | aarch64 |

## 预编译包

| 文件 | 大小 | SHA256 |
|------|------|--------|
| `chezscheme-10.3.0-aarch64-tpb64l.tar.gz` | 9.3M | `22658fad333fe078888b94b5eadd78db3bce0423ab378a12f707d706040e6698` |

路径前缀: `usr/local/`（解压后可直接安装到 `/usr/local`）

## 安装方式

```bash
# 解压到目标根目录（推荐 /）
tar xzf chezscheme-10.3.0-aarch64-tpb64l.tar.gz -C /

# 验证安装
scheme --version  # 应输出: Chez Scheme Version 10.3.0

# 运行Scheme脚本
scheme --script your_script.ss
```

## 安装目录结构

```
$PREFIX/
  bin/
    scheme          → ../lib/csv10.3.0/tpb64l/scheme (符号链接)
    petite          → ../lib/csv10.3.0/tpb64l/petite (符号链接)
    scheme-script   → ../lib/csv10.3.0/tpb64l/scheme-script (符号链接)
  lib/
    csv10.3.0/
      tpb64l/
        scheme        主二进制 (ELF aarch64, ~936KB)
        petite        → scheme (符号链接)
        scheme-script → scheme (符号链接)
        scheme.boot   Scheme boot文件 (~951KB)
        petite.boot   Petite boot文件 (~1.9MB)
        scheme-script.boot → scheme.boot (符号链接)
      examples/      示例程序
```

## 补丁说明

### 0001-makefiles-install.zuo.patch

**类型**: 平台适配
**作用**: 将 `ln -f`（硬链接）改为 `cp`（拷贝），适配不支持硬链接的文件系统
**适用**: HMDFS/嵌入式文件系统等不支持硬链接的场景

## 运行要求

- Linux/鸿蒙 aarch64 系统
- musl libc (ld-musl-aarch64.so.1)
- 无需 ncurses/x11 库

## 功能验证

10项功能测试全部通过，覆盖：
- 版本信息、基础算术（含精确分数）
- 列表操作、字符串操作
- 递归（阶乘/斐波那契）、bytevector/UTF-8
- 文件IO、宏系统、条件判断
- Scheme源码编译(compile-file)与加载执行

## 已知限制

- tunknown 平台标记：无平台特定汇编优化，仅 bytecode 解释器模式
- 无 native 代码生成（pb 架构不使用平台汇编器）
- 符号链接替代硬链接（因文件系统限制）

## 许可证

Apache-2.0

## 来源

- 源码: https://github.com/cisco/chezscheme/archive/refs/tags/v10.3.0.tar.gz
- 构建日期: 2026-05-21