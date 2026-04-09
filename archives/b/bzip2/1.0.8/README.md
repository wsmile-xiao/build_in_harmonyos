# bzip2 编译指南

## 软件信息

| 项目 | 值 |
|------|-----|
| 软件名称 | bzip2 |
| 版本 | 1.0.8 |
| 官网 | https://sourceware.org/bzip2/ |
| 源码下载 | https://sourceware.org/pub/bzip2/bzip2-1.0.8.tar.gz |
| 补丁数 | **1 个**（平台自动检测） |

## 编译环境

- 操作系统: HarmonyOS / OpenHarmony
- 编译器: clang (OHOS SDK)
- 目标架构: aarch64

## 编译步骤

### 1. 下载源码

```bash
wget -O bzip2-1.0.8.tar.gz "https://sourceware.org/pub/bzip2/bzip2-1.0.8.tar.gz"
tar -xzf bzip2-1.0.8.tar.gz
cd bzip2-1.0.8
```

### 2. 应用补丁（1 个：平台自动检测 -fPIC）

> **设计思路**：CC/AR/RANLIB/PREFIX 全部通过 `make` 环境变量覆盖，不修改默认值。
> 唯一的补丁让 CFLAGS **自动检测鸿蒙平台**并追加 `-fPIC`（Linux 上 EXTRA_CFLAGS 为空，行为与原版一致）。

```bash
patch -p1 < patches/0001-Makefile-ohos-autodetect.patch
```

补丁核心逻辑：
```makefile
# 检测 $(CC) -dumpmachine 输出是否包含 "ohos"
EXTRA_CFLAGS := $(shell $(CC) -dumpmachine 2>/dev/null | grep -q "ohos" && echo "-fPIC")
CFLAGS = -Wall -Winline -O2 -g $(BIGFILES) $(EXTRA_CFLAGS)
```

### 3. 编译（纯环境变量，零硬编码）

```bash
# 编译静态库和可执行文件
make CC=clang AR=llvm-ar RANLIB=llvm-ranlib -j$(nproc)

# 编译共享库（Makefile-libbz2_so 已自带 -fPIC，无需修改）
make -f Makefile-libbz2_so CC=clang
```

### 4. 安装

```bash
make install PREFIX=$HOME/usr/local
cp libbz2.so.1.0.8 $HOME/usr/local/lib/

# ⚠️ 鸿蒙 ln -sf 有 bug，必须先删后建
cd $HOME/usr/local/lib
/bin/rm -f libbz2.so libbz2.so.1 libbz2.so.1.0
/bin/ln -s libbz2.so.1.0.8 libbz2.so.1.0
/bin/ln -s libbz2.so.1.0.8 libbz2.so.1
/bin/ln -s libbz2.so.1.0.8 libbz2.so
```

### 一行速查

```bash
make CC=clang AR=llvm-ar RANLIB=llvm-ranlib -j$(nproc) && \
make -f Makefile-libbz2_so CC=clang && \
make install PREFIX=$HOME/usr/local
```

## 补丁说明

### 为什么需要这个补丁？

bzip2 的 `Makefile` 中 CFLAGS 使用**直接赋值**（`=`），不是条件赋值（`?=`）或追加（`+=`）：

```makefile
# 原始写法：直接赋值，make CFLAGS="xxx" 无法追加，只能完全替换
CFLAGS=-Wall -Winline -O2 -g $(BIGFILES)
```

这意味着用户如果用 `make CFLAGS="-O3"` 覆盖，必须**完整复制原值**，漏掉任何选项都会导致问题。

### 补丁方案对比

| 方案 | 做法 | 优点 | 缺点 |
|------|------|------|------|
| ❌ sed 硬编码 | `sed 's/CFLAGS=/...-fPIC/'` | 简单 | Linux 上也带 -fPIC；每次编译都要记命令 |
| ❌ make 参数覆盖 | `make CFLAGS="完整值..."` | 不改文件 | 必须背下完整 CFLAGS；容易遗漏选项 |
| ✅ **平台自动检测（当前）** | 1 个 patch + 环境变量 | 跨平台兼容；AI/人都能一键编译 | 需要一个最小 patch |

## ⚠️ 鸿蒙注意事项

### 1. ln -sf bug

鸿蒙系统的 `ln -sf` 会创建带随机后缀的文件，而不是覆盖现有符号链接：

```bash
# ❌ 错误：ln -sf 会创建 libbz2.so_abc123 这样的文件
ln -sf libbz2.so.1.0.8 libbz2.so

# ✅ 正确：先删除再创建
/bin/rm -f libbz2.so && /bin/ln -s libbz2.so.1.0.8 libbz2.so
```

### 2. 共享库需单独编译

bzip2 默认 Makefile 只编译静态库：

```bash
make                          # 静态库 + 可执行文件
make -f Makefile-libbz2_so   # 共享库（已自带 -fPIC，无需改）
```

## 编译结果

```
$HOME/usr/local/
├── lib/
│   ├── libbz2.a          # 静态库（带 -fPIC，仅鸿蒙）
│   ├── libbz2.so         -> libbz2.so.1.0.8
│   ├── libbz2.so.1       -> libbz2.so.1.0.8
│   ├── libbz2.so.1.0     -> libbz2.so.1.0.8
│   └── libbz2.so.1.0.8   # 动态库
├── include/
│   └── bzlib.h           # 头文件
└── bin/
    ├── bzip2 / bunzip2 / bzcat / bzip2recover
    ├── bzgrep / bzegrep / bzfgrep
    └── bzdiff / bzcmp / bzmore / bzless
```

## 依赖关系

被依赖：Python (_bz2)、tar (.tar.bz2)、dpkg、rpm 等

## 兼容性说明

### 构建系统特点

| 特点 | 说明 |
|------|------|
| 配置方式 | 简单 Makefile（无 configure） |
| 编译器覆盖 | CC=, AR=, RANLIB= (环境变量) |
| 安装路径 | PREFIX= (环境变量) |
| 平台适配 | 1 个补丁：CFLAGS 自动检测 ohos → 加 -fPIC |
| 跨平台 | 同一补丁在 Linux 上无副作用（EXTRA_CFLAGS 为空） |

## 版本历史

| 版本 | 日期 | 说明 |
|------|------|------|
| 1.0.8 | 2019-07-13 | 当前最新稳定版 |
| 1.0.7 | 2019-06-27 | 安全更新 |

## 参考资料

- bzip2 官网：https://sourceware.org/bzip2/
- bzip2 手册：https://sourceware.org/bzip2/manual/manual.html
