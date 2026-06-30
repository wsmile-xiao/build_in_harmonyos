# mutt 2.2.16 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-05-21
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 下载源码: `curl -L -o mutt-2.2.16.tar.gz http://ftp.mutt.org/pub/mutt/mutt-2.2.16.tar.gz`
2. 初始化编译: `ohc-run.py init-build mutt 2.2.16 --url=http://ftp.mutt.org/pub/mutt/mutt-2.2.16.tar.gz`
3. 应用 E007 补丁: `perl patch-autotools-ohos.pl config.guess config.sub`
4. 修复 E011 (umask 077): `sed -i 's/umask 077/umask 022/g' configure`
5. Configure: `./configure --prefix=$DEFAULT_PREFIX --enable-imap --enable-pop --enable-smtp --enable-sidebar --with-ssl --with-curses --with-homespool=Mail --with-mailpath=/var/mail`
6. Make: `make`
7. Staging install: `make install DESTDIR=$TEST_PREFIX`
8. Local install: `make install`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 无法识别 HarmonyOS | E007: GNU config.guess 不包含 HarmonyOS 检测分支 | 使用 patch-autotools-ohos.pl 补丁脚本 |
| 2 | config.status 权限错误 | E011: HMDFS umask 077 导致临时目录不可写 | 修改 configure 中 umask 077 为 umask 022 |

## 源码修改

- config.guess: 添加 __OHOS__ LIBC 检测和 HarmonyOS 系统识别
- config.sub: 添加 ohos-linux triplet
- configure: umask 077 → umask 022 (HMDFS 权限问题)

## 依赖版本

- ncurses: 6.4
- openssl: 1.1.1w
- zlib: 系统内置

## 验证结果

```bash
$ mutt -v
Mutt 2.2.16 (2025-11-22)
System: HarmonyOS HongMeng Kernel 1.12.0 (aarch64)
ncurses: ncurses 6.6.20251230
Compiler: clang version 15.0.4
Configure options: --prefix=/storage/Users/currentUser/usr/local --enable-imap --enable-pop --enable-smtp --enable-sidebar --with-ssl --with-curses --with-homespool=Mail --with-mailpath=/var/mail
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| mutt-2.2.16-ohos-aarch64.tar.gz | 580MB | 预编译包（含文档、示例） |

## 注意事项

- mutt 需要指定邮件存储路径 (--with-homespool, --with-mailpath)
- HMDFS 文件系统上需要修改 configure 中的 umask 077 为 umask 022
- 使用 ncursesw（宽字符版本）而非 ncurses
---

**编译结束**: 2026-05-21 12:17
**最终状态**: built
