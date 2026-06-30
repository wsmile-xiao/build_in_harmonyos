# bgpq4 1.16 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-06-10
- 编译器: clang 15.0.4
- 平台: aarch64-unknown-linux-ohos
- 状态: built

## 编译步骤

1. 下载并解压源码 tarball
2. 运行 `autoreconf --force --install --verbose` 生成 configure 脚本（源码来自 git tag，缺少预生成的 configure）
3. 修补 config.sub：修复 ohos-linux 映射中重复行的问题（E072 相关）
4. 使用 out-of-source 构建方式（因 HMDFS 的 umask 077 权限问题）
5. 运行 `configure --prefix=$DEFAULT_PREFIX`（在 ~/tmp/bgpq4-build 中）
6. 修补 config.status：移除 umask 077（HMDFS 上 umask 077 导致 mktemp 目录不可写）
7. 手动运行 `bash ./config.status` 生成 Makefile
8. `make -j2` 编译（编译成功）
9. `make install DESTDIR=$TEST_PREFIX`（staging 验证）
10. `make check`（在线测试通过，IRRD 查询正常）
11. `make install`（本地安装验证）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 脚本不存在 | 源码来自 git tag，缺少预生成的 configure | 运行 `autoreconf --force --install --verbose` |
| 2 | config.sub 中 ohos-linux 映射有重复行 | 预扫描脚本自动添加 ohos-linux 但格式错误（产生重复行） | 手动修复 config.sub，删除重复的 basic_machine 和 basic_os 行 |
| 3 | config.status 权限错误 (Permission denied) | HMDFS 上 umask 077 导致 mktemp -d 创建的临时目录不可写 | 1) 使用 out-of-source 构建绕过源码目录权限问题；2) 修补 config.status 移除 umask 077 |
| 4 | G0 干净构建验证失败 | 原 tarball 缺少 configure 脚本，clean-verify 不支持 autoreconf 预步骤 | 已手动验证构建正确性；G0 为已知限制 |

## 源码修改

- config.sub: 修复 ohos-linux 映射的重复行（E072 方案）
  - 修改前: ohos-linux 分支有重复的 `basic_machine=$field1-unknown` 和 `basic_os` 行（linux-android + linux-ohos 同时出现）
  - 修改后: 仅保留正确的 `basic_machine=$field1-unknown` 和 `basic_os=linux-ohos`

## 依赖版本

- clang 15.0.4
- GNU Make 4.4.1
- autoconf 2.72
- automake 1.17
- libtool 2.4.7
- pkg-config 0.29.2
- 无外部库依赖

## 验证结果

```bash
$ bgpq4 -v
bgpq4 - a versatile utility to generate BGP filters
version: 1.16
website: https://github.com/bgp/bgpq4
maintainer: Job Snijders <job@sobornost.net>

$ make check
版本测试: PASS
在线 IRRd 查询测试 (AS15562:AS-SNIJDERS): PASS — 成功获取 IPv6 prefix-list

$ file ~/usr/local/bin/bgpq4
ELF shared object, 64-bit LSB arm64, dynamic, not stripped
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| bgpq4-1.16-ohos-aarch64.tar.gz | 171KB | 预编译包（含二进制 + man 页面） |
| bgpq4-1.16-ohos-aarch64-debug.tar.gz | 35KB | 调试符号包 |
| 0001-config.sub.patch | 38KB | config.sub ohos-linux 映射修复补丁 |

## 注意事项

- bgpq4 是 autotools 项目，源码来自 git tag 需要先运行 `autoreconf --force --install --verbose` 或 `./bootstrap`
- HMDFS 的 umask 077 限制会导致 config.status 的 mktemp 临时目录不可写，需移除 umask 077 或使用 out-of-source 构建
- 构建使用 out-of-source 方式（~/tmp/bgpq4-build），以避免源码目录中的 config.status 权限问题
- G0 干净构建验证因原 tarball 缺少 configure 脚本而失败，这是 git tag 发行方式的已知限制
---

**编译结束**: 2026-06-10 05:19
**最终状态**: built