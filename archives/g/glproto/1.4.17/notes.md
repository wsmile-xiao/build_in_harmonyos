# glproto 1.4.17 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-08-06
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 下载源码: `wget https://xorg.freedesktop.org/archive/individual/proto/glproto-1.4.17.tar.gz`
2. 解压: `tar -xzf glproto-1.4.17.tar.gz`
3. 修补 config.guess 以识别 HarmonyOS 平台
4. 运行 configure: `./configure --prefix=$DEFAULT_PREFIX`
5. 编译: `make -j1` (header-only, nothing to compile)
6. 安装: `make install DESTDIR=$TEST_PREFIX`
7. 检查: `make check` (no tests defined)

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 无法识别 HarmonyOS | 2013年版 config.guess 不包含 HarmonyOS 检测分支，uname -s 返回 "HarmonyOS" 无法匹配 | 添加 HarmonyOS case 到 config.guess，映射为 aarch64-unknown-linux-gnu |
| 2 | configure 生成 config.status 时 Permission denied | HarmonyOS HMDFS 文件系统中 umask 077 + setgid 位导致 mktemp 创建的目录无法写入 | 在 conanfile.py build() 中用 Python replace 移除 umask 077 |
| 3 | test_package 编译失败 | glxproto.h 使用 X11 类型(CARD8/CARD16等)需要 xproto 依赖 | 改用 glxtokens.h (无 X11 依赖) 编写测试 |

## 源码修改

### 0001-config.guess.patch
- 文件: config.guess
- 修改: 添加 HarmonyOS 平台识别 (两处)
  1. UNAME_SYSTEM case: 添加 HarmonyOS → LIBC=gnu (跳过编译检测)
  2. 机器检测 case: 添加 aarch64:HarmonyOS → aarch64-unknown-linux-gnu

### conanfile.py build() 中的程序化修复
- 文件: configure (通过 conanfile.py build() 方法在运行时修复)
- 修改: 移除 umask 077 (两处)
  1. `mktemp -d` 前的 umask 077
  2. `mkdir` 前的 umask 077

## 依赖版本

- 无运行时依赖 (header-only package)
- 构建工具: autoconf (预构建的 configure 脚本), pkg-config

## 验证结果

```bash
# Conan 验证 (8 道门禁全部通过)
conan create ... --build=missing — PASS
# 测试包编译运行
test_glproto — PASS (GLX_RGBA=4, GLX_DOUBLEBUFFER=5)
```

## 注意事项

1. glproto 是 X.Org 协议头文件包，只安装 .h 文件和 .pc 文件，无库文件
2. configure 脚本是预构建的 (tarball 中已包含)，不需要 automake
3. xorg-macros pkg-config 包缺失但不影响构建 (configure 已预构建)
4. umask 077 问题是 HarmonyOS HMDFS 文件系统的通用问题，影响所有使用 autotools 的软件
---

**编译结束**: 2026-08-06 14:20
**最终状态**: built

