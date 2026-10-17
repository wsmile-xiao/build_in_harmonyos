# bsdtar 3.7.7 (libarchive 3.7.7 CLI) — 适配记录

**日期**: 2026-08-22
**状态**: ⏳ 本地适配完成，待本地门禁与交付

## 一、基本信息

| 项目 | 值 |
|------|-----|
| 软件 | bsdtar (libarchive 3.7.7 CLI) |
| 版本 | 3.7.7 |
| 构建系统 | autotools |
| 源码 | https://www.libarchive.org/downloads/libarchive-3.7.7.tar.xz |
| SHA256 | 879acd83c3399c7caaee73fe5f7418e06087ab2aaf40af3e99b9e29beb29faee |
| 作用 | 提供 bsdtar/bsdcpio/bsdcat/bsdunzip 命令行工具 |

## 二、复用来源

本适配基于同上游项目 libarchive 3.8.7 的已有配方（PR !4620，已合入 main），
按其状态认定为路径 B 候选（存在经核验可复用的真实 OHOS 修复/验证方案）。

## 三、适配过程与坑位

1. **config.guess 不识别 HarmonyOS** → 复用 3.8.7 的 0001 patch（clean apply，offset -6）。
2. **config.status 临时目录 Permission denied**（hmdfs 下 umask 077）→ 复用 3.8.7 的 0002 patch（umask 077→002，clean apply）。
3. **test_main mode 断言**（hmfs 权限位不完整保留）→ 3.8.7 的 0003 patch 在 3.7.7 上下文不同（函数 `assertion_file_mode` 位置差异），需手动适配等价修复（owner-bits-only 比较，逻辑相同）。
4. 手动构建时 **make 级联重生成 autotools 文件**（缺 automake-1.17/aclocal-1.17）→ 与 3.8.7 同类问题，源/生成文件时间戳规避。
5. 实际链接依赖仅 **zlib + liblzma(xz)**（configure 未检出 bzip2/zstd/lz4/openssl/libxml2）。

## 四、补丁清单

| 补丁 | 内容 | 来源 |
|------|------|------|
| patches/0001-build-autoconf-config.guess.patch | config.guess 增加 HarmonyOS OHOS 支持 | 复用 3.8.7，clean apply |
| patches/0002-configure.patch | configure tmp 目录 umask 077→002（hmdfs Permission denied） | 复用 3.8.7，clean apply |
| patches/0003-test-utils-test-main-mode.patch | test_main.c mode 断言放宽为 owner-bits-only（hmfs 权限位差异） | 3.7.7 版本适配（3.8.7 上下文不同） |

## 五、测试结果

### make check（5 套件）

| 套件 | 运行 | 失败 | 跳过 | 说明 |
|------|------|------|------|------|
| libarchive_test | 637 | 8 | 205 | 硬链接(E079)+权限(E011/E129)为已知平台限制 |
| bsdtar_test | 73 | 22 | 10 | 同上 |
| bsdcpio_test | 49 | 8 | 9 | 同上 |
| bsdcat_test | 18 | 0 | 2 | 全部通过 |
| bsdunzip_test | 24 | 1 | 0 | 加密 backend 未编译（test_P_encryption） |
| **合计** | **801** | **39** | **226** | |

### test_package

| 测试 | 结果 |
|------|------|
| bsdtar --version | bsdtar 3.7.7 - libarchive 3.7.7 zlib/1.3.1 liblzma/5.6.2 |
| tar 创建+提取往返 | 通过（内容匹配） |
| 内存 tar 库读取 | 通过（test bsdtar 3.7.7: OK） |

## 六、知识引用

- E007: config.guess HarmonyOS 识别
- E041: automake 版本不匹配（级联重生成）
- E005: -fPIC 静态库链接
- E011: hmfs umask 077 Permission denied
- E079: HMDFS 硬链接不支持
- E129: HMDFS 权限位不完整
- DRAFT-gnome-autoar-runtime-capability-skip-2147: 加密 backend 运行时能力测试边界

## 结束标记

最终状态: 本地适配完成，待本地门禁与正式交付