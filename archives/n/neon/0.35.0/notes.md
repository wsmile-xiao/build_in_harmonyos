# neon 0.35.0 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-05-25
- 编译器: clang/clang++
- 状态: published

## 编译步骤

1. init-build neon 0.35.0 --url=https://github.com/notroj/neon/archive/refs/tags/0.35.0.tar.gz --no-download
2. 修复 config.guess/config.sub (E007): perl patch-autotools-ohos.pl config.guess config.sub
3. 安装依赖: expat 2.7.1 (cmd-pkgs), openssl 和 zlib 已预装
4. export TMPDIR=/data/storage/el2/base/cache (R10)
5. ./configure --prefix=$DEFAULT_PREFIX --with-ssl=openssl
6. make -j1
7. make install DESTDIR=$TEST_PREFIX
8. make check — 跳过（toybox date 不支持相对日期格式）
9. ohc-run.py package neon 0.35.0
10. make install（无 DESTDIR，本地验证）
11. ohc-run.py finish neon 0.35.0 published

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 无法识别 HarmonyOS | E007: GNU config.guess 不含 HarmonyOS 检测 | patch-autotools-ohos.pl 修复 |
| 2 | config.status Permission denied (mktemp) | HMDFS umask 077 限制 | export TMPDIR=/data/storage/el2/base/cache |
| 3 | make check 失败 | toybox date 不支持 -d '2 days ago' 等相对日期 | 跳过 make check，记录为平台限制 |

## 源码修改

- 0001-config.guess.patch: 添加 __OHOS__ LIBC 检测 + HarmonyOS 系统识别
- 0002-config.sub.patch: 添加 ohos-linux triplet

## 依赖版本

| 依赖 | 版本 | 来源 |
|------|------|------|
| openssl | 3.5.6 | 预装 |
| zlib | 1.3.1 | 预装 |
| expat | 2.7.1 | cmd-pkgs 预编译包 |

## 验证结果

```bash
neon-config --version → 0.35.0
pkg-config --modversion neon → 0.35.0
ls $DEFAULT_PREFIX/lib/libneon.a → 存在
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| neon-0.35.0-ohos-aarch64.tar.gz | 1050295 B | 预编译包 |

## 注意事项

- neon 是纯库（无独立可执行文件），交付物包含 libneon.a + neon-config + neon.pc + 头文件
- make check 需要完整 CA 证书基础设施，在 HarmonyOS 上因 toybox date 限制无法运行
- 使用 expat 作为 XML parser（非 libxml2）
- configure 时必须 export TMPDIR 避免 HMDFS 限制---

**编译结束**: 2026-05-25 20:25
**最终状态**: published
---

**编译结束**: 2026-05-26 10:24
**最终状态**: published
