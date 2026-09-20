# rsyslog 8.2404.0 适配笔记

## 编译环境
- 构建系统: autotools
- 首次手工适配: 2026-05-28（探索性编译，产物未走 conan）
- Conan 配方适配: 2026-09-18
- 编译器: clang/clang++（OHOS SDK, aarch64-unknown-linux-ohos, 原生构建）
- 状态: built

## Conan 依赖（全部已发布到 ohpcd 制品仓）

| 依赖 | 版本 | 用途 | 备注 |
|------|------|------|------|
| libestr | 0.1.11 | 核心字符串库 | 已发布 |
| libfastjson | 1.2609.0 | JSON 库 | **从 1.2304.0 切换**：1.2304.0 从未发布，1.2609.0 已发布且经 CI 验证 |
| libgcrypt | 1.11.0 | lmcry_gcry 加密模块 | 传递依赖 libgpg-error（conan 自动管理） |
| uuid | 2.40.1 | uuid 生成（configure 默认开启，缺失即致命错误） | 制品仓已有 |
| zlib | 1.3.1.1 | gzip 压缩输出（默认特性） | 1.3.1 静态库非 PIC，链入共享模块（lmzlibw.so）报 R_AARCH64 relocation；**1.3.1.1 为 PIC 修订版**（制品仓已有，cairo 同款先例） |

fmhttp（需 libcurl）通过 `--disable-fmhttp` 关闭——libcurl 不在依赖集内。

## 上游测试清点（R51）

- tests/ 目录：1097 个 .sh 测试脚本，tests/Makefile.am 中 130 处 TESTS 声明
- testbench 整体受 `--enable-testbench`（默认 no）门控，还需 `--enable-imdiag` 与运行时守护环境（监听端口、部分测试需 root）
- 默认构建下 `make check` 为空操作；CI 环境无法运行完整 testbench
- test_package 实测：`rsyslogd --version` + `rsyslogd -N1`（配置校验运行）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.status 无法创建临时目录 ./confXXXXXX | HMDFS 权限问题，umask 077 创建的目录不可写 | E011 方案：补丁 0001 将 configure 临时目录块 umask 077 → 000（与 libestr/libfastjson CI 验证过的做法一致） |
| 2 | dnscache.c 等核心文件缺少 pthread_cancel/pthread_setcancelstate | OHOS musl libc 不提供这些函数（sysroot pthread.h 无声明、libc.so 无符号，已编译验证） | 补丁 0002-0006 用 HAVE_PTHREAD_CANCEL 条件编译；该宏保持未定义 → 走 rsyslog 内建的非取消式线程终止回退路径 |
| 3 | config.guess 无法识别系统（uname -s = HarmonyOS） | 2018 版 config.guess/sub 不认识 HarmonyOS/linux-ohos | 补丁 0007/0008 添加 *:HarmonyOS:* 分支与 linux-ohos 识别 |
| 4 | configure 报 "libgcrypt-config not found / libestr not met" | conan 依赖包内嵌 .pc/*-config 记录 prefix=/（DESTDIR 式安装），路径不可用；libestr/libfastjson 的 cpp_info.libs 名有误 | generate() 用 pkg.m4 环境变量（LIBESTR_CFLAGS 等）注入真实 conan 包路径；libgcrypt 用生成的 libgcrypt-config 包装器（LIBGCRYPT_CONFIG 指向） |
| 5 | 源码包下载随机截断 | www.rsyslog.com 无 Content-Length，该网络类别下连接随机中断；且 conandata 原 sha256 (b172a309...) 有误（此前从未校验过） | 实测完整文件 sha256=30528d14...（rsyslog.com 与 Yocto 镜像双源验证一致）；conandata 用 URL 列表：官方源优先 + Yocto 源镜像回退，conan 按 sha256 逐 URL 校验切换 |
| 6 | 历史补丁在 conan 下无法应用 | 原补丁用 rsyslog-8.2404.0.orig/.work 前缀，conan 的 patch_ng 以 strip=0 应用且只自动剥 a/ b/ 前缀 | 全部补丁重新生成为 a/ b/ 格式（内容不变），已用 patch_ng strip=0 逐一验证 8/8 通过 |

## 源码修改（相对上游）

- configure: 临时目录 umask 修复（0001）
- runtime/dnscache.c、runtime/queue.c、runtime/wti.c、runtime/net.c、threads.c: HAVE_PTHREAD_CANCEL 条件编译（0002-0006）
- config.guess、config.sub: HarmonyOS 平台识别（0007/0008）

## 与 2026-05-28 手工适配的差异

- 手工适配曾修改 plugins/imdiag/imdiag.c、plugins/imfile/imfile.c、plugins/omprog/omprog.c——这些插件默认关闭（configure default=no），默认构建不编译，故 conan 配方不含这些补丁
- 手工适配将 configure 临时目录重定向到 $TMPDIR/build-tmp；conan 配方改为仅放宽 umask（去掉对 TMPDIR 环境变量的依赖，CI 环境不保证 TMPDIR 已设置）

## 验证结果

- 8 个补丁经 patch_ng（conan 实际应用机制）strip=0 全量验证通过
- 本地 conan create（ohos-aarch64 profile）验证见 reports/
- test_package: rsyslogd --version + rsyslogd -N1 配置校验

## 注意事项

- 鸿蒙系统缺少 pthread_cancel 系列函数，这是平台限制（musl 裁剪）
- HMDFS 文件系统对临时目录权限有特殊要求（E011）
- 依赖包内嵌 .pc/config 路径不可用是 conan 打包 DESTDIR 安装的通病，下游 autotools 软件需环境变量注入
---

**编译结束**: 2026-09-18 03:00
**最终状态**: built
