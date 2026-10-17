# libarchive 3.8.7 — 适配记录

**日期**: 2026-08-07
**状态**: ✅ 已适配（依赖项 PR，供 pixz 使用）

## 一、基本信息
| 项目 | 值 |
|------|-----|
| 软件 | libarchive |
| 版本 | 3.8.7 |
| 构建系统 | autotools |
| 源码 | https://www.libarchive.org/downloads/libarchive-3.8.7.tar.xz |
| SHA256 | d3a8ba457ae25c27c84fd2830a2efdcc5b1d40bf585d4eb0d35f47e99e5d4774 |
| 作用 | pixz 硬依赖（tar 索引功能），提供 libarchive 库 + bsdtar/bsdcpio/bsdcat/bsdunzip |

## 二、适配过程与坑位

1. **config.guess 不识别 HarmonyOS** → configure 报 `cannot guess build type`。
   补丁 `0001`：给 config.guess 增加 HarmonyOS 分支（aarch64 → aarch64-unknown-linux-ohos）。
   同时 configure 显式传 `--build=aarch64-unknown-linux-gnu` 兜底。
2. **config.status 临时目录 Permission denied**（hmdfs 下 `umask 077` 建出的目录组无写权限，
   当前用户写不进）→ 补丁 `0002`：configure 中 `umask 077` → `umask 002`。
3. 手动构建时 **make 级联重生成 autotools 文件**（缺 automake-1.17/aclocal-1.17）
   → 用源文件时间戳设为旧（2020）、生成文件设为新的方式规避重生成。
4. 实际链接依赖仅 **zlib + liblzma(xz)**（configure 未检出 bzip2/zstd/lz4/openssl/libxml2），
   配方 requirements 只声明 zlib/1.3.1 + xz/5.6.2。

## 三、补丁清单
| 补丁 | 内容 |
|------|------|
| patches/0001-build-autoconf-config.guess.patch | config.guess 增加 HarmonyOS OHOS 支持 |
| patches/0002-configure.patch | configure tmp 目录 umask 077→002（hmdfs Permission denied） |

## 结束标记
最终状态: published (依赖项 PR)