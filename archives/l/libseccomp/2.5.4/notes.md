# libseccomp 2.5.4 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-08-31
- 编译器: clang/clang++（OHOS SDK llvm，/data/service/hnp/bin）
- 目标: HarmonyOS PC aarch64（triplet aarch64-unknown-linux-ohos）
- 状态: built

## 编译步骤

1. 下载源码：https://github.com/seccomp/libseccomp/releases/download/v2.5.4/libseccomp-2.5.4.tar.gz（sha256 d82902400405cf0068574ef3dc1fe5f5926207543ba1ae6f8e7a1576351dcbdb）
2. 应用 13 个补丁（见下）
3. `./configure --prefix=... --enable-static --disable-shared`（AutotoolsToolchain 生成 aarch64-unknown-linux-ohos 工具链）
4. `make -j1`
5. `make install`（staging 到 package_folder）
6. `conan test`（test_package 编译链接并运行纯用户态 API）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 无法识别平台 | 2018 版 config.guess 无 OpenHarmony 分支（E007） | 0001 补丁增加 `*:HarmonyOS:*:*` 检测，输出 aarch64-unknown-linux-ohos |
| 2 | config.sub 把 linux-ohos 归一化成 linux-gnu-ohos | `linux*` 归一化规则把 -ohos 当成版本号 | 0002 补丁接受 linux-ohos / ohos-linux |
| 3 | config.status 生成阶段 mktemp-d 失败 | HMDFS 临时目录限制（E112） | 0003 补丁改用 $HOME/tmp 固定临时目录 |
| 4 | tests/tools 脚本 bad interpreter | OHOS 无 /bin/bash（E087） | 0004-0013 补丁将 `#!/bin/bash` 改为绝对 bash 路径 |

## 源码修改

- 0001-build-aux-config.guess.patch：config.guess 增加 HarmonyOS 检测（uname -s 返回 HarmonyOS）
- 0002-build-aux-config.sub.patch：config.sub 接受 aarch64-unknown-linux-ohos triplet（linux-ohos*、ohos-linux）
- 0003-configure.patch：绕过 HMDFS mktemp-d 临时目录限制
- 0004-0013：src/tests/tools 脚本 shebang 修正为 /data/service/hnp/bin/bash（共 10 处）

## 依赖版本

- 无外部 conan 依赖（dependencies: []）；纯 C 库，仅依赖 libc + Linux 内核头文件

## 测试结果

- 上游 `make check`：sim 系列纯用户态回归测试可运行；真实 seccomp 过滤器测试依赖内核 seccomp/BPF 特性，在受限沙箱验证有限（如实记录，不阻塞构建）
- 消费者验证（test_package）：编译 test_seccomp.c 链接 -lseccomp 并运行，真实调用 seccomp_version()（struct scmp_version，major/minor/micro）与 seccomp_api_get()

## 选型说明

- 2.5.5 / 2.5.6 / 2.6.1 已在 main，2.6.0 分支被 HarmonyOS Developer 占用；2.5.4 是最新的未占用版本
