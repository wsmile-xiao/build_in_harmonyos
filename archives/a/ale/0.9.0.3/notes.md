# ale 0.9.0.3 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-08-05
- 编译器: clang/clang++ (OHOS SDK 26.0.0.18)
- 状态: built

## 编译步骤
1. `./configure --build=aarch64-linux-gnu --host=aarch64-linux-ohos --prefix=/`
2. 修补 configure 脚本 shebang (#! /bin/sh -> /data/service/hnp/bin/bash)
3. 修补 config.status 临时目录创建 (mktemp -> echo ".")
4. `make -j1`
5. `make install`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess/sub 无法识别 HarmonyOS | 2008 年版脚本不含 OHOS 检测 | 更新为新版 config.guess/sub |
| 2 | configure 脚本 shebang 错误 | /bin/sh 为 minimal shell，不支持函数语法 | 改为 /data/service/hnp/bin/bash |
| 3 | config.status 无法创建临时文件 | SELinux 限制 mktemp | 使用当前目录代替 mktemp |
| 4 | VERSION 文件遮蔽系统 <version> 头 | -I. 导致 VERSION 被误认为系统头文件 | 改用 -iquote . |
| 5 | #include <config.h> 找不到 | -iquote 只影响引号包含 | 全部改为 #include "config.h" |
| 6 | make 内置规则误将 ale 脚本当二进制链接 | ale 是 shell 脚本包装器 | 添加显式 ale 目标规则 |
| 7 | pthread_cancel 不可用 | OHOS 不支持 pthread_cancel | 改用共享标志位（stop_flag）+ pthread_join 协作式退出 |

## 源码修改
- 0001-Makefile.in.patch: -I. -> -iquote .，移除 config.status 自动重生成
- 0002-ale.cc.patch: <config.h> -> "config.h"
- 0003-config.guess.patch: 更新 OHOS 识别
- 0004-config.h.in.patch: 更新 OHOS 配置
- 0005-config.sub.patch: 更新 OHOS/aarch64 识别
- 0006-d3-focus.h.patch: C++11 窄化转换修复
- 0007-lib-c-ctype.c.patch: <config.h> -> "config.h"
- 0008-lib-strerror.c.patch: <config.h> -> "config.h"
- 0009-lib-strndup.c.patch: <config.h> -> "config.h"
- 0010-lib-strnlen.c.patch: <config.h> -> "config.h"
- 0011-lib-strtod.c.patch: <config.h> -> "config.h"
- 0012-ui-input.h.patch: <config.h> -> "config.h"
- 0013-ui-ui_tty.h.patch: pthread_cancel 改用共享标志位（stop_flag）+ pthread_join（R8 合规）

## 依赖版本
- 无外部依赖（仅系统库：libm, libpthread, libstdc++）

## 验证结果
- configure: 通过 (aarch64-unknown-linux-ohos)
- make: 通过 (ale-bin 生成)
- test_package: 1/1 通过 (ale-bin --version)

## 注意事项
- E165 shebang 问题已在 conan recipe 的 build() 方法中处理
- G0 干净构建中 configure 因 E165 产生警告，不影响实际构建
---
**编译结束**: 2026-08-05
**最终状态**: built