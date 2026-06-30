# mp3gain 1.6.2 适配笔记

## 编译环境
- 构建系统: makefile
- 编译日期: 2026-05-29
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 初始化编译: `ohc-run.py init-build mp3gain 1.6.2 --url=https://github.com/Sound-Linux-More/mp3gain/archive/refs/tags/1.6.2.tar.gz`
2. 安装依赖 mpg123 1.32.9 (从源码编译安装到 ~/usr/local)
3. 修改 Makefile 添加 PREFIX/DESTDIR 支持
4. 编译: `make CFLAGS="-Wall -DHAVE_MEMCPY -fPIC -O2 -I$PREFIX/include" LDFLAGS="-L$PREFIX/lib -Wl,-rpath,$PREFIX/lib"`
5. DESTDIR安装: `make install PREFIX=$DEFAULT_PREFIX DESTDIR=$TEST_PREFIX`
6. 本地安装验证: `make install PREFIX=$DEFAULT_PREFIX` (无DESTDIR)
7. 功能验证: `mp3gain --version` → "mp3gain version 1.6.2"
8. 打包: `ohc-run.py package mp3gain 1.6.2`
9. 收尾: `ohc-run.py finish mp3gain 1.6.2 built`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 缺少 libmpg123 | mpg123未预装 | 从源码编译安装 mpg123 1.32.9 |
| 2 | mpg123 configure config.guess 不识别 HarmonyOS | E007: config.guess 无 __OHOS__ 分支 | 用 patch-autotools-ohos.pl 打补丁 |
| 3 | mpg123 config.sub 拒绝 linux-ohos 三元组 | config.sub 缺少 kernel-os 组合中的 linux-ohos* | 手动添加 linux-ohos* 到 kernel-os 组合列表 |
| 4 | mpg123 config.status 创建临时文件 Permission denied | E011: HMDFS umask 077 导致 UID 映射不匹配 | sed -i 's/umask 077/umask 022/g' configure |
| 5 | mp3gain 无 configure 脚本 | mp3gain 使用简单 Makefile | 修改 Makefile 添加 PREFIX/DESTDIR 支持 |
| 6 | mp3gain 无 make check 目标 | 简单 Makefile 项目无测试套件 | 手动功能验证 mp3gain --version |

## 源码修改

- **0001-Makefile-add-PREFIX-DESTDIR-support.patch**: 修改 Makefile 添加 PREFIX/DESTDIR 变量支持，修改 INSTALL_PATH 为 $(DESTDIR)$(PREFIX)/bin，在 install 目标中添加 mkdir -p

## 依赖版本

- mpg123/1.32.9 (手动编译安装)

## 验证结果

```bash
$ mp3gain --version
mp3gain version 1.6.2

$ mp3gain -v
mp3gain version 1.6.2
copyright(c) 2001-2009 by Glen Sawyer
uses mpglib, which can be found at http://www.mpg123.de
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| mp3gain-1.6.2-ohos-aarch64.tar.gz | 389KB | 预编译包（stripped） |
| mp3gain-1.6.2-ohos-aarch64-debug.tar.gz | 92KB | debug symbols 包 |

## 注意事项

- mp3gain 运行时依赖 libmpg123.so，需确保 mpg123 已安装
- mp3gain 无 make check 目标，建议运行时验证功能
- G0 干净构建验证失败因 mp3gain 无 configure 脚本（Makefile 项目特性）
---

**编译结束**: 2026-05-29 11:07
**最终状态**: built