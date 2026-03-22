# GDBM 1.23 鸿蒙系统编译指南

## 一、概述

GDBM (GNU DataBase Manager) 是一个轻量级的键值对数据库库，使用可扩展哈希算法实现。它是 Python 3.9 的 `_gdbm` 模块的依赖库。

## 二、软件信息

| 项目 | 值 |
|------|-----|
| 软件名称 | gdbm |
| 版本 | 1.23 |
| 官方网站 | https://www.gnu.org/software/gdbm/ |
| 下载地址 | https://ftp.gnu.org/gnu/gdbm/gdbm-1.23.tar.gz |
| 构建系统 | Autotools (configure) |

## 三、鸿蒙环境

| 项目 | 值 |
|------|-----|
| 系统版本 | HarmonyOS HongMeng Kernel 1.11.0 |
| 架构 | aarch64 |
| 编译器 | Clang 15.0.4 |
| 工具链 | LLVM (llvm-ar, llvm-ranlib, llvm-nm) |

## 四、编译步骤

### 4.1 解压源码

```bash
cd $HOME/build
mkdir -p gdbm && cd gdbm
curl -LO https://ftp.gnu.org/gnu/gdbm/gdbm-1.23.tar.gz
tar -xzf gdbm-1.23.tar.gz
```

### 4.2 创建工作目录

```bash
mv gdbm-1.23 orig
cp -a orig work
cp -a orig verify
```

### 4.3 应用补丁

```bash
cd work
patch -p1 < /path/to/0001-config.guess-add-HarmonyOS-support.patch
patch -p1 < /path/to/0002-config.sub-add-HarmonyOS-support.patch
```

### 4.4 配置

```bash
export PREFIX=$HOME/usr/local
export CFLAGS="-fPIC"

./configure \
    --prefix=$PREFIX \
    --enable-libgdbm-compat \
    --disable-nls
```

**关键选项说明：**

| 选项 | 说明 |
|------|------|
| `--enable-libgdbm-compat` | 生成兼容 libgdbm_compat 库，提供 dbm/ndbm 兼容接口 |
| `--disable-nls` | 禁用国际化支持（避免对 libintl 的依赖） |
| `CFLAGS="-fPIC"` | 生成位置无关代码（静态库链接到共享库时必需） |

### 4.5 编译和安装

```bash
make -j$(nproc)
make install
```

### 4.6 修复符号链接

```bash
cd $HOME/usr/local/lib
ln -sf libgdbm.so.6.0.0 libgdbm.so
ln -sf libgdbm.so.6.0.0 libgdbm.so.6
ln -sf libgdbm_compat.so.4.0.0 libgdbm_compat.so
ln -sf libgdbm_compat.so.4.0.0 libgdbm_compat.so.4
```

## 五、补丁说明

### 5.1 修改文件

1. **build-aux/config.guess**: 添加 HarmonyOS 系统检测
2. **build-aux/config.sub**: 添加 linux-ohos 目标支持

### 5.2 关键修改详解

#### config.guess - HarmonyOS 检测

**问题背景**: autotools 的 `config.guess` 脚本无法识别 HarmonyOS 系统，导致生成错误的三元组。

**解决方案**: 在 `i*86:Minix:*:*` 分支之前添加 HarmonyOS 检测逻辑：

```bash
*:HarmonyOS:*:*)
    # HarmonyOS/OpenHarmony detection
    # Output triplet: {MACHINE}-unknown-linux-ohos
    case "$UNAME_MACHINE" in
        aarch64|arm64)
            echo "aarch64-unknown-linux-ohos"
            ;;
        armv7*|arm*)
            echo "arm-unknown-linux-ohos"
            ;;
        x86_64|amd64)
            echo "x86_64-unknown-linux-ohos"
            ;;
        i?86)
            echo "i686-unknown-linux-ohos"
            ;;
        *)
            echo "$UNAME_MACHINE-unknown-linux-ohos"
            ;;
    esac
    exit ;;
```

**三元组格式**: `{架构}-unknown-linux-ohos`
- `aarch64-unknown-linux-ohos` (ARM64)
- `x86_64-unknown-linux-ohos` (x86_64)

#### config.sub - linux-ohos 支持

**问题背景**: `config.sub` 无法识别 `linux-ohos` 操作系统标识。

**解决方案**: 在三处添加支持：

1. **KERNEL-OS 组合识别**（第 118 行附近）:
```bash
nto-qnx* | linux-ohos* | linux-gnu* | linux-android* | ...
```

2. **-linux-ohos 处理**（第 1420 行附近）:
```bash
-linux-ohos)
    os=-linux-ohos
    ;;
```

3. **-harmonyos 别名处理**（第 1531 行附近）:
```bash
-harmonyos)
    os=-linux-ohos
    ;;
```

## 六、遇到的问题

### 问题 1: libintl 链接失败

**现象**:
```
ld.lld: error: undefined symbol: libintl_gettext
ld.lld: error: undefined symbol: libintl_bindtextdomain
ld.lld: error: undefined symbol: libintl_textdomain
```

**原因**: gdbm 默认启用 NLS（国际化），需要 libintl 库。虽然系统已安装 libintl.a，但链接时未正确引入。

**解决方案**: 使用 `--disable-nls` 禁用国际化支持。对于命令行工具，国际化不是必需的功能。

### 问题 2: 共享库加载失败

**现象**:
```
Error loading shared library libgdbm.so.6: No such file or directory
```

**原因**: 动态链接器找不到共享库路径。

**解决方案**: 
1. 设置 `LD_LIBRARY_PATH`: `export LD_LIBRARY_PATH=$HOME/usr/local/lib:$LD_LIBRARY_PATH`
2. 或使用静态库编译: `clang ... $HOME/usr/local/lib/libgdbm.a`

## 七、安装结果

### 7.1 安装的文件

```
$HOME/usr/local/
├── include/
│   ├── gdbm.h          # 主头文件
│   ├── dbm.h           # dbm 兼容接口
│   └── ndbm.h          # ndbm 兼容接口
└── lib/
    ├── libgdbm.a       # 静态库
    ├── libgdbm.so      # 共享库（符号链接）
    ├── libgdbm.so.6    # 共享库（符号链接）
    ├── libgdbm.so.6.0.0  # 共享库
    ├── libgdbm_compat.a   # 兼容静态库
    ├── libgdbm_compat.so  # 兼容共享库
    ├── libgdbm_compat.so.4
    └── libgdbm_compat.so.4.0.0
```

### 7.2 库大小

| 文件 | 大小 |
|------|------|
| libgdbm.a | 149 KB |
| libgdbm.so.6.0.0 | 125 KB |
| libgdbm_compat.a | 24 KB |
| libgdbm_compat.so.4.0.0 | 27 KB |

## 八、经验总结

### 8.1 与其他项目的关联

| 依赖项目 | 用途 |
|----------|------|
| Python 3.9 | `_gdbm` 模块依赖此库 |

### 8.2 编译注意事项

1. **必须使用 `-fPIC`**: 静态库被链接到共享库时必需
2. **推荐禁用 NLS**: 避免 libintl 依赖问题
3. **安装兼容库**: `--enable-libgdbm-compat` 提供 dbm/ndbm 兼容接口

### 8.3 与类似项目对比

| 项目 | 特点 |
|------|------|
| gdbm | GNU 实现，单文件数据库 |
| Berkeley DB | 功能更丰富，支持事务 |
| lmdb | 高性能，内存映射 |

## 九、参考资料

- GDBM 官方手册: https://www.gnu.org/software/gdbm/manual/
- GDBM 源码: https://ftp.gnu.org/gnu/gdbm/
- Python dbm 模块文档: https://docs.python.org/3/library/dbm.html

---

*文档生成时间: 2026-03-21*