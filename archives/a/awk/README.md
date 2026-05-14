# awk (onetrueawk) — OpenHarmony 预编译包

## 简介

awk (onetrueawk) 是 AWK 编程语言的经典实现，由 Brian Kernighan 维护。本页面提供在 HarmonyOS/OpenHarmony aarch64 平台的预编译版本。

## 基本信息

| 属性 | 值 |
|------|-----|
| 软件 | awk (onetrueawk) |
| 源码 | https://github.com/onetrueawk/awk |
| 构建系统 | Makefile |
| 目标平台 | ohos-aarch64 |
| 无依赖 | 无第三方依赖 |

## 可用版本

| 版本 | 状态 | 发布日期 | 补丁数 |
|------|------|----------|--------|
| 20251225 | ✅ success | 2025-12-26 | 0 |

## 快速安装

```bash
# 解压预编译包
tar xzf awk-20251225-ohos-aarch64.tar.gz -C ~/usr/local

# 进入目录并安装
cd ~/usr/local/awk-20251225-ohos-aarch64
sh install-awk-20251225.sh

# 验证安装
awk --version
# 输出: awk version 20251225
```

## 编译指导

### 特殊说明

1. **Makefile 项目**: awk 使用简单 Makefile，无 configure 脚本
2. **手动安装**: 需手动复制 `a.out` 到目标目录并重命名为 `awk`
3. **编译器设置**: 需显式设置 `CC=clang` 和 `CFLAGS=-O2`

### 编译步骤

```bash
# 下载源码
wget https://github.com/onetrueawk/awk/archive/refs/tags/20251225.tar.gz
tar xzf 20251225.tar.gz
cd awk-20251225

# 编译
export CC=clang
export CFLAGS=-O2
export HOSTCC=clang
make -j$(nproc)

# 安装
mkdir -p ~/usr/local/bin ~/usr/local/share/man/man1
cp a.out ~/usr/local/bin/awk
cp awk.1 ~/usr/local/share/man/man1/
```

## 补丁清单

当前版本无补丁，源码可直接编译。

## 已知限制

1. **/tmp 只读**: 测试套件部分测试因 `/tmp` 只读而失败（平台限制）
2. **命令缺失**: 测试依赖的 `who`、`locale` 命令不可用（环境限制）
3. 以上限制不影响 awk 核心功能

## 功能验证

```bash
# 版本检查
awk --version
# awk version 20251225

# 基本文本处理
echo "hello world" | awk '{print $1}'
# hello

# 字段处理
echo -e "test\ndata" | awk '{print NR": "$0}'
# 1: test
# 2: data

# 正则替换
echo "foo123bar" | awk '{gsub(/[0-9]+/, "NUM"); print}'
# fooNUMbar

# 数组统计
echo -e "a\nb\na\nc" | awk '{count[$1]++} END {for(k in count) print k, count[k]}'
# a 2
# b 1
# c 1
```

## 测试状态

| 测试类别 | 通过数 | 总数 | 通过率 |
|----------|--------|------|--------|
| 基础测试 (t.*) | 166 | 167 | 99.4% |
| 正则测试 (p.*) | 58 | 58 | 100% |
| UTF 测试 (T.utf) | 106 | 106 | 100% |
| UTF 正则 (T.utfre) | 194 | 194 | 100% |
| 性能测试 (tt.*) | 21 | 21 | 100% |
| **总计** | **545** | **546** | **99.8%** |

## 相关链接

- [源码仓库](https://github.com/onetrueawk/awk)
- [AWK 书籍](https://ia902302.us.archive.org/25/items/addisonwesleyprofessionalunix_201704/addisonwesleyprofessionalunix.pdf)
- [RELEASENOTE](RELEASENOTE.md)