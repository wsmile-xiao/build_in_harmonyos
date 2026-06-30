# autoconf-archive 2024.10.16 — 适配笔记

## 平台
- 目标: OpenHarmony (aarch64, musl libc)
- 构建系统: autotools (纯 M4 宏集合，无 C 代码)

## 编译步骤
1. 应用 3 个已有补丁 (configure, stamp-vti, version.texi)
2. `./configure --prefix=$DEFAULT_PREFIX`
3. `make -j2` (doc 构建因 makeinfo Perl 模块路径问题跳过)
4. `cp m4/*.m4 $PREFIX/share/aclocal/` (手动安装宏文件)

## 关键信息
- 总共安装 594 个 M4 宏文件 (586 个 ax_* 宏)
- 安装路径: $PREFIX/share/aclocal/
- autoconf 可通过 `aclocal` 自动发现这些宏

## 已知限制
- doc/Makefile 因 makeinfo 的 Perl Texinfo::ModulePath 模块未正确加载而失败
- 文档安装可跳过，不影响宏文件使用

## 验证
```
$ ls /usr/local/share/aclocal/ | wc -l
594
$ ls /usr/local/share/aclocal/ax_*.m4 | wc -l
586
```
