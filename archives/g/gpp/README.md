# GPP - General-purpose Preprocessor

## 软件信息

- **软件名**: gpp
- **全名**: General-purpose Preprocessor
- **版本**: 2.28
- **描述**: 通用预处理器，具有可自定义语法。支持 C/C++、TeX、HTML、Prolog 等多种操作模式。
- **主页**: https://logological.org/gpp
- **许可证**: GPL-3.0-or-later
- **作者**: Denis Auroux (1996-2001), Tristan Miller (2003-2020)

## 构建信息

- **构建系统**: autotools
- **源码URL**: https://files.nothingisreal.com/software/gpp/gpp-2.28.tar.bz2
- **格式**: tar.bz2
- **依赖**: 无（仅依赖 libc）

## OpenHarmony 适配要点

### 关键问题

1. **lld 链接器 libxml2 缺失**: OHOS SDK 的 lld 链接器依赖 libxml2.so.16（系统缺失），需使用 `LDFLAGS="-fuse-ld=bfd"` 切换到 bfd 链接器。

2. **conftest 无法执行（E064）**: configure 生成的 conftest 程序需要 ELF 签名才能在 HarmonyOS 上执行。修改 configure 脚本，在执行 conftest 前调用 `ohc-run.py sign-elf` 签名。

3. **HMDFS 临时目录限制**: config.status 在 HMDFS 上无法在当前目录创建临时子目录（Permission denied），需将 tmp 变量指向 ~/tmp。

4. **不创建补丁（R2）**: 以上修改均针对 autotools 生成的文件（configure、config.status），不创建补丁。

### 编译参数

```bash
export LDFLAGS="-fuse-ld=bfd -L/storage/Users/currentUser/usr/local/lib"
export CFLAGS="-fPIC -O2"
export CPPFLAGS="-I/storage/Users/currentUser/usr/local/include"
./configure --prefix=/storage/Users/currentUser/usr/local
make -j1
make install DESTDIR=/storage/Users/currentUser/tmp/test-install-gpp-2.28
```

## 功能特性

gpp 支持以下操作模式：
- **默认模式**: `#define x y` 和 `macro(arg,...)`
- **C兼容模式 (-C)**: 最大 C 预处理器兼容性
- **TeX模式 (-T)**: `\define{x}{y}` 和 `\macro{arg}{...}`
- **HTML模式 (-H)**: `<#define x|y>` 和 `<#macro arg|...>`
- **XHTML模式 (-X)**: `<#define x|y/>` 和 `<#macro arg|.../>`
- **Prolog模式 (-P)**: Prolog 兼容的 C 预处理器模式
- **用户自定义 (-U)**: 可自定义语法

## 版本历史

| 版本 | 状态 | 日期 | 备注 |
|------|------|------|------|
| 2.28 | published | 2026-06-04 | HarmonyOS aarch64 编译成功 |