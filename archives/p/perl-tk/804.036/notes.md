# perl-tk 804.036 适配笔记

## 编译环境
- 构建系统: makefile (Perl MakeMaker)
- 编译日期: 2026-06-04
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 下载源码: Tk-804.036.tar.gz from cpan.metacpan.org
2. 解压到 ~/tmp/builds/perl-tk-804.036.work
3. 安装 X11 依赖: libX11, libXau, xorgproto, libXext
4. 运行: `perl Makefile.PL X11LIB=~/usr/local/lib X11INC=~/usr/local/include`
5. 编译: `make` (修复 PNG/zlib/Makefile 中 AR=llvm-ar → AR=llvm-ar rcs)
6. 安装: `make install DESTDIR=$TEST_PREFIX`
7. 打包: `ohc-run.py package perl-tk 804.036`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | perl Makefile.PL 失败找不到X11 | 缺少 X11 依赖库 | 安装 libX11/libXau/xorgproto/libXext 并设置 X11LIB/X11INC |
| 2 | make 编译失败 llvm-ar error | llvm-ar 需要操作标志 rcs | 修改 PNG/zlib/Makefile: AR=llvm-ar → AR=llvm-ar rcs |
| 3 | make test 无法运行 | 需要 X11 display server | 跳过测试 (GUI toolkit，无法在 headless 环境测试) |

## 源码修改

- `PNG/zlib/Makefile`: AR=llvm-ar → AR=llvm-ar rcs (补丁: 0001-PNG-zlib-Makefile.patch)

## 依赖版本

| 依赖 | 版本 | 说明 |
|------|------|------|
| perl | 5.42.0 | OpenHarmony 预装 |
| libX11 | 6.4.0 | cmd-pkgs/curl 安装 |
| libXau | 6.0.0 | cmd-pkgs/curl 安装 |
| xorgproto | 2024.1 | cmd-pkgs/curl 安装 |
| libXext | 6.4.0 | cmd-pkgs/curl 安装 |

## 验证结果

```bash
# Staging 安装验证
$ find $TEST_PREFIX/bin -type f → 5 个二进制文件 (gedi, ptked, ptksh, tkjpeg, widget)
$ find $TEST_PREFIX/lib -name "*.so" → 25+ 个 XS 共享库模块
$ find $TEST_PREFIX/lib -name "*.pm" → 200+ 个 Perl 模块文件
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| perl-tk-804.036-ohos-aarch64.tar.gz | ~10MB | 预编译包 (stripped) |
| perl-tk-804.036-ohos-aarch64-debug.tar.gz | ~1MB | 预编译包 (debug symbols) |

## 注意事项

- perl-tk 是 Perl 模块，不是独立二进制软件，使用 PERL5LIB 路径查找
- GUI toolkit 模块无法在 headless 环境运行测试
- llvm-ar 在所有 Perl MakeMaker 子 Makefile 中需要添加 rcs 操作标志

---

**编译结束**: 2026-06-04 11:15
**最终状态**: built
---

**编译结束**: 2026-06-04 11:17
**最终状态**: built
