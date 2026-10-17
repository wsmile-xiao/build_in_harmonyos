# pax 20240817 — OpenHarmony 编译记录

## 基本信息
- 软件: pax (paxmirabilis)
- 版本: 20240817
- 构建系统: custom (Build.sh)
- 目标: ohos-aarch64
- 源码: https://launchpadlibrarian.net/744756412/pax_20240817.orig.tar.gz

## 编译方式
pax uses a custom Build.sh script that auto-detects platform features and compiles
all source files directly. Build command: `CC=clang CFLAGS="-fPIC -O2" sh Build.sh -r`

## 补丁说明
- patches/0001-Build.sh.patch: Add fts.c to SRCS list for portable fts implementation
- patches/0002-tar.c.patch: Fix uid/gid fallback when nobody user unavailable on OHOS

## 已知限制
- Hard links (pax→cpio→tar) may fail on OHOS due to filesystem restrictions
  (cp is used as fallback automatically)
- uid/gid values > 2097151 are replaced with 65534 in ustar headers
  (OHOS uses large uids like 20020099)

## 功能验证
- Create archive: `pax -w -x ustar -f archive.tar dir/` ✓
- List archive: `pax -f archive.tar` ✓
- Extract archive: `pax -r -f archive.tar` ✓
