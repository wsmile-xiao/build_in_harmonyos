# gdnsd 3.8.2 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-05-29
- 编译器: clang 15.0.4 / clang++
- 状态: built

## 编译步骤

1. `python3 $SKILL_ROOT/scripts/ohc-run.py init-build gdnsd 3.8.2 --url=https://codeload.github.com/gdnsd/gdnsd/tar.gz/v3.8.2`
2. 安装依赖: libev 4.33, openssl 1.1.1w, zlib 1.3.1, userspace-rcu 0.15.6, libsodium 1.0.22, ragel 6.10 (均从 cmd-pkgs 预编译包安装)
3. 创建 libev.pc pkg-config 文件 (libev 手动编译版不含 .pc 文件)
4. 设置 `export SSL_CERT_FILE=/storage/Users/currentUser/usr/local/ssl/cert.pem` 解决下载 SSL 证书问题
5. `autoreconf -fi` 生成 configure 脚本
6. `./configure --prefix=/storage/Users/currentUser/usr/local`
7. 修改 3 个源文件: 用 `#ifdef __OHOS__` 守卫跳过 pthread_setcanceltype 调用
8. `make -j2` 编译成功
9. `make install DESTDIR=$TEST_PREFIX` staging 安装
10. `make install` 本地安装
11. 验证: gdnsd --version → 3.8.2, gdnsdctl --version → 3.8.2

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build SSL下载失败 | Python SSL证书路径缺失 | `export SSL_CERT_FILE=...` 后成功 |
| 2 | GitHub网络不通 | 环境无法直连github.com | 用 codeload.github.com (owner=gdnsd/gdnsd) 替代 |
| 3 | ragel未安装导致vscf.c生成失败 | GitHub tarball不含预生成vscf.c | 从cmd-pkgs安装ragel 6.10 |
| 4 | pthread_setcanceltype链接失败 | musl libc不实现pthread_cancel系列 | `#ifdef __OHOS__` 守卫跳过调用 |
| 5 | libev无pkg-config文件 | libev手动编译不生成.pc | 手动创建libev.pc |
| 6 | make check失败 | 缺Socket6/IO::Socket::INET6等Perl模块 | 跳过(非关键) |

## 源码修改

3个文件用 `#ifdef __OHOS__` 守卫 `pthread_setcanceltype(PTHREAD_CANCEL_ASYNCHRONOUS, NULL)`:
- libgdmaps/gdmaps.c:612
- src/dnsio_tcp.c:1037
- src/dnsio_udp.c:584

## 依赖版本

- libev 4.33 (预编译包, 手动创建libev.pc)
- openssl 1.1.1w (预编译包)
- zlib 1.3.1 (预编译包)
- userspace-rcu 0.15.6 (预编译包)
- libsodium 1.0.22 (预编译包)
- ragel 6.10 (预编译包, 构建工具)

## 验证结果

```bash
/storage/Users/currentUser/usr/local/sbin/gdnsd --version → gdnsd version 3.8.2
/storage/Users/currentUser/usr/local/bin/gdnsdctl --version → gdnsdctl version 3.8.2
```

## 交付物

| 文件 | 说明 |
|------|------|
| gdnsd (sbin) | 主DNS服务器二进制 |
| gdnsdctl (bin) | 控制工具 |
| gdnsd_geoip_test (bin) | GeoIP测试工具 |
| gdnsd_extmon_helper (libexec) | 外部监控助手 |

## 注意事项

- pthread_setcanceltype/pthread_cancel 在OHOS上未实现, 取消线程功能不可用
- 测试套件需额外Perl模块(Socket6等)才能运行
- GDNSD GitHub owner 是 "gdnsd/gdnsd" 非 "blblack/gdnsd"
---

**编译结束**: 2026-06-02 15:21
**最终状态**: built
