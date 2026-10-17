# pmix

## 简介
PMIx (Process Management Interface for Exascale) 是面向超算的进程管理接口标准，为 MPI 等并行编程模型提供可移植的进程管理 API。

## OHOS 适配
- 5.0.11 使用上游 Autotools 构建系统（autoconf/automake），官方 release tarball。
- 平台识别：tarball 自带 config.guess/config.sub (2021-01-25) 不认识 ohos，补丁在 config.guess 增加 HarmonyOS 识别分支、config.sub 三处 ohos 白名单（ohos-linux 映射 / OS 白名单 ohos* / kernel-os 白名单 linux-ohos*）。
- HMDFS 限制：config.guess 与 configure 内嵌 config.status 模板以 umask 077 运行 mktemp，创建的 0700 属主临时目录在 HMDFS 上连属主都不可写，补丁将 umask 077→022（E011）。
- 依赖 libevent 和 hwloc，通过 Conan 管理依赖链（--with-libevent/--with-hwloc 指向 conan package_folder）；zlib 为可选组件，系统缺失不阻塞，与上游行为一致不加 require。
- 构建产物包含 libpmix 共享库（libpmix.so.2.13.11）和 9 个命令行工具：pmix_info、pattrs、palloc、pctrl、pevent、plookup、pmixcc、pps、pquery（--enable-pmix-binaries）。

## 依赖
- libevent/2.1.12
- hwloc/2.14.0

## 功能验证
```bash
# 版本冒烟（pmix_info --version 走 CLI help 机制只打印帮助文本，用无参数输出的 "PMIX: 5.0.11" 行断言）
pmix_info | grep "PMIX: 5.0.11"

# 端到端 API（simptest server 模式：无服务器时 PMIx_Init 返回 UNREACH(-25) 属预期，
# 须 PMIx_server_init → PMIx_server_register_client → PMIx_server_setup_fork →
# fork 子进程带 server env 后 PMIx_Init/PMIx_Finalize）
conan create archives/p/pmix/5.0.11 --build=missing
```

## 与 5.0.10 / 5.0.7 的关系
- upstream main 已有他人 5.0.10 归档（半成品），本目录仅新增 5.0.11，不动 5.0.10。
- upstream feat/pmix-5.0.7 为他人历史分支，本适配曾参考其软件级文件结构与依赖组合（只读参考，非本协作者所推）。

## 许可
BSD-3-Clause

## 参考
- 主页: https://pmix.org/
- 源码: https://github.com/openpmix/openpmix
