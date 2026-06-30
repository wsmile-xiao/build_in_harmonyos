# isync 1.5.1 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-05-26
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 下载源码: SourceForge isync-1.5.1.tar.gz
2. 更新 config.guess/config.sub（使用 automake-1.16 版本）
3. 配置: `./configure --prefix=$DEFAULT_PREFIX --with-ssl=$HOME/usr/local --with-zlib=$HOME/usr/local`
4. 编译: `make -j1`
5. 测试: `make check` (PASS: 3)
6. 安装: `make install DESTDIR=$TEST_PREFIX`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 无法识别系统 | OpenHarmony 未被识别 | 使用 automake-1.16 的最新 config.guess |
| 2 | getpass 函数不可用 | musl libc 未实现 getpass | 添加 getpass 替代实现（使用 termios） |

## 源码修改

### src/drv_imap.c
添加了 getpass() 函数的替代实现，用于 OpenHarmony 系统：
- 使用 termios 禁用终端回显
- 从 /dev/tty 或 stdin/fdout 读取密码
- 返回静态缓冲区中的密码字符串

## 依赖版本

- openssl/1.1.1 (已安装)
- zlib/1.3 (已安装)

## 验证结果

```bash
$ mbsync --version
isync 1.5.1

$ file mbsync
ELF shared object, 64-bit LSB arm64, dynamic (/lib/ld-musl-aarch64.so.1), not stripped
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| mbsync | 289KB | IMAP 邮箱同步工具 |
| mbsync-get-cert | 1.5KB | 获取 SSL 证书脚本 |

## 注意事项

- OpenHarmony 使用 musl libc，缺少部分 POSIX 函数
- 密码输入功能已适配，但建议使用 PassCmd 配置选项
---

**编译结束**: 2026-05-26 20:09
**最终状态**: built
