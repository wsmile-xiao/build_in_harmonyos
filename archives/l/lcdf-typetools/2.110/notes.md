# lcdf-typetools 2.110 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-06-09
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 下载源码: wget https://www.lcdf.org/type/lcdf-typetools-2.110.tar.gz
2. 解压到 ~/tmp/lcdf-typetools-build（避免 HMDFS 权限问题）
3. 设置 TMPDIR: export TMPDIR=/data/storage/el2/base/cache
4. 运行 configure: ./configure --prefix=$DEFAULT_PREFIX --without-kpathsea
5. 修改 config.status 使用 TMPDIR（第592、596行）
6. 运行 make -j1
7. 运行 make install DESTDIR=$TEST_PREFIX（staging）
8. 运行 make install（本地验证）
9. 验证所有11个可执行文件 --version

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 缺少 kpathsea 库 | TeX 依赖未安装 | 使用 --without-kpathsea 禁用 |
| 2 | config.status 无法创建临时文件 | HMDFS 文件系统 SELinux 限制 | 修改 config.status 使用 $TMPDIR |
| 3 | SSL 证书验证失败 | 下载时证书问题 | 使用 wget 直接下载 |

## 源码修改

修改 config.status 脚本（第592、596行）：
- 第592行: mktemp -d "./confXXXXXX" → mktemp -d "$TMPDIR/confXXXXXX"
- 第596行: tmp=./conf$$-$RANDOM → tmp=$TMPDIR/conf$$-$RANDOM

**注意**: 这是 autotools config.status 的临时文件路径问题，需要在所有 HMDFS 文件系统上应用。

## 依赖版本

- 无外部依赖（禁用了 kpathsea）
- 编译器: clang 15.0.4
- make: GNU Make 4.4.1
- autotools: autoconf 2.72, automake 1.16.5

## 验证结果

```bash
# 所有11个工具验证成功
cfftot1 --version → LCDF typetools 2.110
mmafm --version → LCDF typetools 2.110
mmpfb --version → LCDF typetools 2.110
otfinfo --version → LCDF typetools 2.110
otftotfm --version → LCDF typetools 2.110
t1dotlessj --version → LCDF typetools 2.110
t1lint --version → LCDF typetools 2.110
t1rawafm --version → LCDF typetools 2.110
t1reencode --version → LCDF typetools 2.110
t1testpage --version → LCDF typetools 2.110
ttftotype42 --version → LCDF typetools 2.110
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| lcdf-typetools-2.110-ohos-aarch64.tar.gz | 16MB | 预编译包 |

## 注意事项

1. 必须设置 TMPDIR=/data/storage/el2/base/cache 避免 HMDFS 权限问题
2. 建议在 ~/tmp 目录编译，避免 HMDFS 文件系统限制
3. otftotfm 功能受限（禁用了 kpathsea），其他工具正常工作
---

**编译结束**: 2026-08-27 01:23
**最终状态**: built
---

**编译结束**: 2026-08-27 01:25
**最终状态**: built
