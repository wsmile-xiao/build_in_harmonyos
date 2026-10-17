# ssmtp 2.64 适配笔记

## 编译环境
- 构建系统: autotools (autoconf 2.13)
- 编译日期: 2026-09-17（第二轮：恢复 SSL 支持）
- 编译器: clang/clang++
- 状态: published

## 编译步骤

```bash
CC=clang CFLAGS="-fPIC -O2 -Wno-int-conversion -Wno-void-pointer-to-int-cast -Wno-pointer-sign -Wno-array-bounds" \
  LIBS="-L<openssl-lib> -lssl -lcrypto" \
  ./configure --prefix=$HOME/usr/local --enable-ssl --enable-md5auth --enable-inet6 --enable-logfile
make -j1
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `(char)NULL` 编译错误 | ssmtp.c 有27处 `(char)NULL`，现代 clang 视为 int-conversion 错误 | CFLAGS 加 `-Wno-int-conversion` 等警告抑制 |
| 2 | Makefile 不支持 DESTDIR | 旧 Makefile.in 无 DESTDIR 前缀 | conanfile.py package() 手动安装 |
| 3 | generate_config 失败 | 脚本使用 `hostname --fqdn`，OpenHarmony 不支持 | 跳过 generate_config，创建默认 ssmtp.conf |
| 4 | Makefile 不读取 env CFLAGS | 旧 autoconf 2.13 Makefile 在 configure 时捕获 CFLAGS | build() 中用正则追加 -Wno flags 到 Makefile |
| 5 | 不支持 VPATH 构建 | autoconf 2.13 configure 无 out-of-source 支持 | layout() 中设 build=source |
| 6 | 链接行不含 LDFLAGS | 链接行为 `$(CC) -o ssmtp $(OBJS) @LIBS@ $(CFLAGS)`，无 LDFLAGS | openssl 的 -L/-lssl/-lcrypto 通过 LIBS 环境变量在 configure 时捕获进 @LIBS@ |
| 7 | Makefile 不捕获 CPPFLAGS | @CFLAGS@ 只含 configure 时 env CFLAGS，-I 丢失 | Makefile 正则补丁同时追加 openssl -I 路径 |
| 8 | SSL 曾被禁用 | 2026-09-02 时 openssl 未发布到 ohpcd 制品仓 | 2026-08 起 openssl/1.1.1w 已发布（含 OHOS aarch64 二进制），恢复 with_ssl=True 默认，无裁剪 |

## SSL 适配说明（2026-09-17 恢复）

- openssl/1.1.1w（静态库 libssl.a/libcrypto.a）从 ohpcd 制品仓拉取
- 链接顺序关键：`-lssl -lcrypto`（静态链接 ssl 依赖 crypto，顺序不能反）
- configure 的 `--enable-ssl` 只做两件事：定义 HAVE_SSL + 追加 `-lssl` 到 LIBS，无任何检测
- 二进制体积从 ~51KB（无 SSL）增至 ~2.5MB（静态链接 openssl）
- 验证判据：`grep -qa STARTTLS <binary>` — 无 SSL 构建不含该字符串（对照实验验证）

## 验证结果

```bash
$ ssmtp -V
sSMTP 2.64 (Not sendmail at all)

$ nm ssmtp | grep -c SSL_
596

$ readelf -d ssmtp | grep NEEDED
Shared library: [libc.so]     # openssl 静态链接，无运行时依赖污染
```

## 上游测试清点（R51）

上游 ssmtp 2.64 源码无任何测试套件：
- Makefile.in 无 check/test 目标
- 源码树无 tests/ 目录与测试源文件
- test_package 测试为本仓库补全：`ssmtp -V` 冒烟 + STARTTLS SSL 验证（2 项断言）

## 注意事项

- ssmtp 是命令行工具（application），非库（library）
- SSL 静态链接 openssl，运行时仅依赖 libc.so

## 最终状态

COMPLETED - ssmtp 2.64 适配完成（含 SSL/TLS 支持），conan-verify 全部通过，二进制可用。
---

**编译结束**: 2026-09-17 12:40
**最终状态**: published
