# spin — 软件说明

## 基本信息

| 项目 | 值 |
|------|-----|
| **软件名** | spin |
| **版本** | 6.5.2 |
| **描述** | Efficient verification tool of multi-threaded software — Promela/Nanoscript 模型验证器 |
| **主页** | https://spinroot.com/ |
| **源码** | https://github.com/nimble-code/Spin |
| **许可证** | BSD-like (see Src/license) |
| **构建系统** | makefile（自定义 Makefile，无 configure） |

## 功能概述

Spin 是广泛使用的形式化验证工具，主要用于：

- **Promela 模型验证**: 验证并发/多线程软件的正确性
- **LTL 公式检查**: 支持线性时序逻辑（Linear Temporal Logic）属性验证
- **状态空间探索**: 自动搜索反例和死锁
- **模拟执行**: 单步或随机模拟 Promela 模型行为
- **验证器生成**: `-a` 选项生成 C 语言验证器（pan.c）

## OpenHarmony 适配说明

### 编译要点

1. **bison -y**: spin Makefile 使用 `y?tab.c` 通配模式，需要 `YACC="bison -y"` 强制 yacc 传统输出
2. **-fuse-ld=bfd**: OHOS SDK 的 ld.lld 有 libxml2.so.16 依赖问题，需切换到 ld.bfd
3. **install -D**: spin Makefile install 目标不创建父目录，需 `INSTALL="install -D"` 自动创建

### 平台限制

- spin -run/-search 模式默认使用 gcc 作为 C 预处理器
- OHOS 平台无 gcc，需使用 `-P` 参数指定 clang 包装脚本或安装 gcc
- 此限制不影响 spin 核心功能（模型生成、语法解析、模拟）

### 安装文件

```
/storage/Users/currentUser/usr/local/
├── bin/spin        # 主可执行文件 (1.2M)
└── share/man/man1/spin.1  # 手册页 (12K)
```

## 预编译包

- `spin-6.5.2-ohos-aarch64.tar.gz` (1.2M): 预编译二进制 + man 页
- `spin-6.5.2-ohos-aarch64-debug.tar.gz` (58K): 调试符号