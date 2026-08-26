# webalizer 2.23.08 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-08-09
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 安装 Conan 依赖: `conan install --requires="gd/2.3.3" -pr:h=ohos-aarch64 -r=ohpcd --build=missing`
2. 设置环境变量:
   - CPPFLAGS 指向 zlib/libpng/gd 的 include 目录
   - LDFLAGS 指向 zlib/libpng/gd 的 lib 目录
3. 运行 configure: `./configure --prefix=$DEFAULT_PREFIX --disable-dns --disable-bz2 --disable-geoip`
4. 编译: `make -j1`
5. 安装: `make install DESTDIR=$TEST_PREFIX`
6. 验证: `webalizer -V` 输出版本信息

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.status 无法创建临时文件 | HMDFS 文件系统不支持 umask 077 创建的目录内写入文件 | 补丁修改 configure 脚本，使用 umask 022 和 TMPDIR 路径 |
| 2 | 找不到源码下载地址 | webalizer.org 官方下载不可用 | 使用 GitHub hyc/webalizer 仓库，master 分支即 2.23-08 版本 |
| 3 | 缺少 libdb 依赖 | DNS 功能需要 Berkeley DB | 禁用 DNS 功能 (--disable-dns) |

## 源码修改

- patches/0001-fix-tmpdir-umask-for-hmdfs.patch: 修复 HMDFS 兼容性

## 依赖版本

- gd/2.3.3
- libpng/1.6.58 (gd 传递依赖)
- zlib/1.3.1.1 (gd 传递依赖)

## 验证结果

```bash
$ webalizer -V
Webalizer V2.23-08 (HarmonyOS HongMeng Kernel 1.12.0 aarch64) English
Copyright 1997-2013 by Bradford L. Barrett
```

## 交付物

| 文件 | 说明 |
|------|------|
| bin/webalizer | 主程序 |
| bin/wcmgr | DNS 缓存管理工具 |
| bin/webazolver | webalizer 符号链接 |
| etc/webalizer.conf.sample | 配置示例 |
| man/man1/webalizer.1 | man 页 |
| man/man1/wcmgr.1 | man 页 |

## 注意事项

- DNS 功能已禁用（缺少 libdb），如需启用需先适配 Berkeley DB
- 源码使用 GitHub hyc/webalizer 仓库，master 分支即版本 2.23-08
- HMDFS 兼容性问题通过补丁解决，详见 patches/
---

**编译结束**: 2026-08-09 02:05
**最终状态**: built
**更新**: 2026-08-25 rebase on latest main, fix url placeholder and patch error message
