# netcat-openbsd 1.234.1 适配笔记

## 编译环境
- 构建系统: makefile (BSD Makefile → GNU Makefile via Debian patches)
- 编译日期: 2026-08-07
- 编译器: clang/clang++
- 状态: published

## 编译步骤

1. 下载源码: netcat-openbsd_1.234.orig.tar.gz (from snapshot.debian.org)
2. 应用 Debian 补丁序列 (16个补丁):
   - port-to-linux-with-libbsd.patch: 平台移植, 添加平台守卫
   - build-without-TLS-support.patch: 移除TLS依赖 (libtls不可用)
   - connect-timeout, dccp-support, broadcast-support 等功能补丁
3. 提供 OHOS 兼容函数 (ohos-compat.c/h):
   - strtonum: 字符串转数字 (BSD)
   - readpassphrase: 终端密码读取 (BSD)
   - explicit_bzero: 安全清零 (BSD)
   - b64_ntop: Base64编码 (resolver库)
4. make -j1 CC=clang

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | bsd/readpassphrase.h not found | OHOS 无libbsd | 提供ohos-compat.h内联声明 |
| 2 | strtonum undefined | OHOS libc无此函数 | ohos-compat.c实现 |
| 3 | explicit_bzero undefined | OHOS libc无此函数 | ohos-compat.c实现 |
| 4 | b64_ntop undefined | OHOS libresolv无此函数 | ohos-compat.c实现 |
| 5 | TLS不可用 | libtls来自LibreSSL, 制品仓无 | 按Debian方式构建不含TLS |

## 源码修改

- patches/0001-Makefile.patch: 替换BSD make为GNU make, 添加ohos-compat.c编译, install目标
- patches/0003-netcat.c.patch: 平台守卫, 移除TLS, 使用ohos-compat.h
- patches/0004-socks.c.patch: 类型修正, 使用ohos-compat.h
- conanfile.py内联提供ohos-compat.c/h (无需外部依赖)

## 依赖版本

无外部Conan依赖 (自包含配方)
- 系统库: libresolv (-lresolv)

## 验证结果

```bash
$ nc -h
usage: nc [-46CDdFhklNnrStUuvZz] [-I length] [-i interval] ...
```

## 注意事项

- TLS支持未包含 (libtls来自LibreSSL, 制品仓中不可用, 同Debian官方包做法)
- 如需TLS支持, 需先适配并发布LibreSSL/libtls
- 配方完全自包含, 无需libbsd依赖
---

**编译结束**: 2026-08-07 04:58
**最终状态**: published

**CI Retry**: Triggering new build after SSL infrastructure failure
