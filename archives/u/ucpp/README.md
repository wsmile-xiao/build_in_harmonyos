# ucpp — C 预处理器

## 描述

ucpp 是一个符合 ISO-C99 标准的 C 预处理器，它是严格且内存占用小的预处理器实现。

## 版本

| 版本 | 状态 | 编译日期 | 备注 |
|------|------|---------|------|
| 1.3.5 | built | 2026-06-15 | 需要 autogen.sh 生成 configure |

## 使用方式

```bash
# 通过预编译包安装（推荐）
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- ucpp 1.3.5

# 或手动编译
cd ucpp-1.3.5
AUTOM4TE=autom4te ./autogen.sh
./configure --prefix=$HOME/usr/local
make -j$(nproc)
make install
```

## 功能

- 符合 ISO-C99 标准的预处理
- 支持宏定义、条件编译、文件包含
- 内存占用小，适合嵌入式系统
- 可作为独立预处理器或嵌入其他编译器

## 依赖

- automake 1.16.5+
- autoconf 2.72+
- libtool 2.4.6+

## 注意事项

- 原始 tarball 不包含 configure，需要运行 autogen.sh
- 编译时需设置 AUTOM4TE=autom4te 环境变量
- clang -Werror 需要修复源码中的严格原型警告

## 来源

- 源码：https://gitlab.com/scarabeusiv/ucpp
- 许可证：BSD-3-Clause