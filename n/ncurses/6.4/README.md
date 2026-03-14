# ncurses 6.4 鸿蒙系统编译指南

## 概述

本文档记录了 ncurses 6.4 在鸿蒙系统上的编译适配过程，包括遇到的问题、解决方案和注意事项。

## 软件信息

- **软件名称**: ncurses
- **版本**: 6.4
- **构建系统**: Autotools (configure)
- **下载地址**: https://ftp.gnu.org/gnu/ncurses/ncurses-6.4.tar.gz

## 鸿蒙环境

- **系统**: HarmonyOS
- **内核**: HongMeng Kernel 1.11.0
- **架构**: aarch64
- **编译器**: Clang 15.0.4
- **工具链**: LLVM (llvm-ar, llvm-ranlib, llvm-nm, llvm-strip)

## 编译步骤

### 1. 解压源码

```bash
tar -xzf ncurses-6.4.tar.gz
cd ncurses-6.4
```

### 2. 应用补丁

```bash
patch -p1 < 0001-port-for-ohos.patch
```

### 3. 配置

```bash
./configure --prefix=$HOME/usr/local \
    --with-shared \
    --enable-widec \
    --enable-pc-files \
    --with-pkg-config-libdir=$HOME/usr/local/lib/pkgconfig
```

### 4. 编译

```bash
make
```

### 5. 安装

```bash
make install
```

## 补丁说明

### 修改文件

1. **config.guess**: 添加 HarmonyOS 系统检测
2. **config.sub**: 添加 `linux-ohos` 三元组支持

### 关键修改

#### config.guess

在 Linux 检测之前添加 HarmonyOS 检测：

```bash
*:HarmonyOS:*:*)
    case "$UNAME_MACHINE" in
        aarch64|arm64)
            MACHINE=aarch64
            ;;
        armv7*|armv8*)
            MACHINE=arm
            ;;
        x86_64|amd64)
            MACHINE=x86_64
            ;;
        i?86)
            MACHINE=i686
            ;;
        *)
            MACHINE="$UNAME_MACHINE"
            ;;
    esac
    GUESS=${MACHINE}-unknown-linux-ohos
    ;;
```

#### config.sub

1. 在有效操作系统列表中添加 `ohos*`
2. 在内核-操作系统验证中添加 `linux-ohos*`

## 遇到的问题

### 问题 1: toybox sed 与 autotools 不兼容

**现象**: 
- 子目录 Makefile 中的 `top_srcdir` 被错误设置为乱码
- config.status 生成的复杂 sed 脚本在 toybox sed 上执行异常

**原因**:
- 鸿蒙使用 toybox sed，而非 GNU sed
- autotools 生成的 config.status 包含复杂的 sed 脚本（多行命令块、分支命令等）
- toybox sed 对这些高级特性的支持可能不完整

**解决方案**:
- 在 configure 完成后，使用脚本自动修复子目录 Makefile 中的 `top_srcdir` 值

```bash
for dir in ncurses include man progs panel menu form test misc c++; do
    if [ -f "$dir/Makefile" ]; then
        perl -pi -e 's/^top_srcdir\s*=.*/top_srcdir\t= ../' "$dir/Makefile"
    fi
done
```

### 问题 2: 临时目录不可写

**现象**: configure 过程中无法创建临时文件

**解决方案**: 设置 `TMPDIR` 环境变量

```bash
export TMPDIR=$HOME/tmp
mkdir -p $TMPDIR
```

## 经验总结

### 鸿蒙 vs Linux 差异

| 方面 | Linux | HarmonyOS |
|------|-------|-----------|
| sed | GNU sed | toybox sed |
| awk | gawk/mawk | toybox awk |
| shell | bash | mksh/sh |
| 临时目录 | /tmp 可写 | 需要设置 TMPDIR |

### 注意事项

1. **toybox 工具兼容性**: 鸿蒙使用 toybox 提供的基础工具，与 GNU 工具存在差异，特别是：
   - sed: 不完全支持 GNU sed 的高级特性
   - awk: 功能有限
   - shell: 默认非 bash

2. **环境变量**: 确保设置正确的环境变量
   - `TMPDIR`: 临时目录
   - `CC`, `CXX`, `AR`, `RANLIB`, `NM`, `STRIP`: 编译工具链

3. **configure 后处理**: 对于使用复杂 autotools 的项目，可能需要在 configure 后手动修复生成的 Makefile

## 编译产物

编译成功后生成以下库文件：

- libncursesw.so.6.4 - 主库（宽字符版本）
- libformw.so.6.4 - 表单库
- libmenuw.so.6.4 - 菜单库
- libpanelw.so.6.4 - 面板库
- libncurses++w.a - C++ 绑定（静态库）

## 参考资料

- ncurses 官方文档: https://invisible-island.net/ncurses/
- GNU config: https://git.savannah.gnu.org/cgit/config.git/
- 鸿蒙编译知识库: build_in_harmonyos/SKILL.md

## 版本历史

- 2026-03-14: 初始版本，完成 ncurses 6.4 鸿蒙适配