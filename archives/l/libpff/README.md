# libpff

Personal Folder File（PFF）格式库与工具集（Library to access the Personal Folder File format）。

## 简介

libpff 是 libyal 取证家族中读取 Microsoft Outlook 邮件存储格式的库，纯 C 编写，
支持读取个人文件夹文件（.pst，PFF）与脱机文件夹文件（.ost，OST）：消息、附件、
文件夹树、复用项（recovered items）等。随库提供两个命令行工具：`pffinfo`
（输出存储元数据）与 `pffexport`（导出项目/条目为文件与 CSV 清单）。

## 官网

https://github.com/libyal/libpff

## 许可证

LGPL-3.0-or-later

## 编译信息

| 版本 | 状态 | 编译日期 | 构建系统 | 补丁数 |
|------|------|----------|----------|--------|
| 20231205 | built | 2026-09-20 | autotools | 0（平台适配在配方 build() 内联完成） |

### 平台适配说明

| 问题 | 说明 | 解决方案 |
|------|------|----------|
| 三元组 | 自带 config.guess/config.sub（2023）不识别 HarmonyOS | 构建期传 `--build/--host=aarch64-unknown-linux-gnu`（本版本 config.sub 拒绝 linux-ohos，已现场取证） |
| E011 | HMDFS 上 umask 077 临时目录创建者无法写入 | configure 内 `umask 077`→`022`，全程 umask 022 |
| E087 | HMDFS 禁止直接执行源码树脚本、设备无 /bin/bash | CONFIG_SHELL 解释 configure；make check 传 LOG_COMPILER=/data/service/hnp/bin/bash |
| E027 | NLS 依赖 gettext（设备无 gettext-devel） | `--disable-nls` |
| zlib | 压缩流为可选自动探测项 | 命中 OHOS NDK sysroot 的 zlib.h/-lz，能力保留 |

### 源码来源说明

上游官方 GitHub release 资产 `libpff-alpha-20231205.tar.gz`（R39 官方源头口径）。
Debian `libpff_20231205-1.dsc`（PGP 签名）锚定的 orig tar.xz 与该资产解包后全树
1074 个文件逐文件 sha256 一致（Debian 仅重压缩），溯源见版本级 notes.md。

## 依赖

无外部 Conan 依赖。发布包自包含 17 个 libyal 本地组件（libbfio、libcdata、
libcerror、libcfile、libclocale、libcnotify、libcpath、libcsplit、libcthreads、
libfcache、libfdata、libfdatetime、libfguid、libfmapi、libfvalue、libfwnt、
libuna），压缩流走系统 zlib（OHOS NDK sysroot 内置）。
Python（pypff）与 Java（jpff）绑定构建期显式关闭。
