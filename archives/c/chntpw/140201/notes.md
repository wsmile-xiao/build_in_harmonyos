# chntpw 140201 适配笔记

## 编译环境
- 构建系统: raw Makefile（无 configure；上游面向 x86 Linux）
- 编译日期: 2026-09-10
- 编译器: clang（OHOS aarch64）
- 状态: built

## 编译步骤

1. Conan 配方 build()：make 命令行变量覆写（codonw 先例）——
   `make CC=clang CFLAGS='-DUSEOPENSSL -g -I. -I<openssl-include> -Wall' OSSLPATH=<openssl包目录> LIBS='-L<openssl-lib> -lcrypto' chntpw reged cpnt samusrgrp sampasswd`
   仅构建 5 个动态工具目标，避开 .static（需 -static + libcrypto.a）
2. package()：上游无 install 目标 → 按交付清单手动拷贝 5 个工具至 bin/（clzip 家族先例）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游 Makefile CFLAGS 强制 -m32 | 上游面向 x86 Linux | make 变量覆写 CFLAGS（去 -m32，保留 -DUSEOPENSSL 并指向包内 openssl 头） |
| 2 | Makefile LIBS=-L$(OSSLLIB) 缺 -lcrypto | 上游注释暗示静态直挂 libcrypto.a | 覆写 LIBS="-L... -lcrypto"（DES_/MD4_ 符号需要） |
| 3 | tarball 自带 4 个陈旧 .static 预编译 ELF | 上游发布习惯 | 只构建动态目标；.static 不入包（package() 白名单拷贝） |
| 4 | pool 同名 chntpw_140201.orig.tar.gz 是 280 字节 HTML 404 页 | 发行版 pool 文件陷阱 | 正源用 .orig.tar.xz（SHA256 与 Debian/Ubuntu dsc 双重一致），下载后 od 看文件头校验 |
| 5 | 官方站 pogostick.net 部分网络不可达 | 上游站点稳定性 | conandata 用 archive.ubuntu.com pristine 源（PF7 允许域），决策链记录 |

## 源码修改

无源码补丁（patches/ 为空）。全部平台适配经 make 命令行变量覆写完成。

## 依赖版本

- 运行依赖：openssl/1.1.1w（libcrypto；chntpw.c:82-83 无条件 include <openssl/des.h>/<openssl/md4.h>，-DUSEOPENSSL 宏本身在代码中零引用）
- 构建工具依赖：无（raw make）

## 验证结果

上游测试（静态清点）：

```text
Makefile 无 test/check 目标；源码树无测试目录/文件
上游静态声明测试数 = 0
```

消费者测试 test_package（test.c）1 个：chntpw -h（rc=0 + usage 特征串）、
reged -h（rc=0 + "Modes:"）、chntpw 无参（rc=1）、sampasswd -h（rc=0）——
断言点均对应上游源码行号（chntpw.c:1047/1056、reged.c:105、sampasswd.c:160）。

## 注意事项

- -DUSEOPENSSL 为遗留摆设宏（代码零引用），但 OpenSSL 头/库依赖真实存在且无条件。
- OpenSSL 3.x 亦可提供 DES_/MD4_（弃用告警非错误）；本配方选用制品仓已有 1.1.1w（alpine 先例）。
- R38：tool 类型，commands.json 已声明 5 个工具。
- tarball 内 .static 预编译产物已在构建目标选择与打包白名单双重排除。
---

**编译结束**: 2026-09-10 23:31
**最终状态**: built
