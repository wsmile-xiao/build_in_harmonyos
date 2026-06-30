# msmtp 1.8.32 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-05-25
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 下载源码: msmtp-1.8.32.tar.xz (官方源)
2. 初始化编译环境: `ohc-run.py init-build msmtp 1.8.32`
3. 修复 config.guess/config.sub: 使用 `patch-autotools-ohos.pl` 添加 HarmonyOS 支持
4. 配置: `./configure --prefix=$DEFAULT_PREFIX`
5. 编译: `make -j2`
6. 安装: `make install DESTDIR=$TEST_PREFIX` (staging) + `make install` (本地)

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 无法识别 HarmonyOS | GNU config.guess 不包含 __OHOS__ 检测 | 使用 `patch-autotools-ohos.pl` 补丁 |
| 2 | 缺少 getpass() 函数 | musl libc 不提供 GNU 扩展 getpass() | 添加 #ifdef __OHOS__ 替代实现 (E093) |
| 3 | 缺少 TLS 支持 | GnuTLS 未安装 | 暂不处理，基础功能可用 |

## 源码修改

| 补丁文件 | 修改内容 |
|----------|----------|
| 0001-build-aux-config.guess.patch | 添加 __OHOS__ LIBC 检测 + HarmonyOS 系统识别 |
| 0002-build-aux-config.sub.patch | 添加 ohos-linux 三元组支持 |
| 0003-src-password.c.patch | 添加 getpass() 替代实现 (musl 兼容) |

## 依赖版本

- gettext/gettext: 已安装 (NLS 支持)
- libiconv: 已安装
- libintl: 已安装

## 验证结果

```bash
$ msmtp --version
msmtp version 1.8.32
Platform: aarch64-unknown-linux-ohos
TLS/SSL library: none
Authentication library: built-in
Supported authentication methods: plain external oauthbearer cram-md5 login xoauth2

$ msmtpd --version
msmtpd version 1.8.32
```

## 测试结果

- test-basic.sh: PASS
- test-auth-plain.sh: FAIL (临时文件权限问题)
- test-header-handling.sh: FAIL (临时文件权限问题)

## 注意事项

1. 当前版本无 TLS 支持，需要额外安装 GnuTLS 才能发送加密邮件
2. getpass() 替代实现不关闭终端回显，安全性较低（建议使用环境变量传递密码）
3. msmtpd 是一个简单的 SMTP 服务器，可用于本地测试

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| msmtp-1.8.32-ohos-aarch64.tar.gz | 811KB | 预编译包（含 msmtp、msmtpd） |
| msmtp-1.8.32-ohos-aarch64-debug.tar.gz | 88KB | 调试符号包 |

---

**编译结束**: 2026-05-25 20:54
**最终状态**: built
---

**编译结束**: 2026-05-25 20:52
**最终状态**: built
