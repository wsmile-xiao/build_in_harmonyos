# x3270 4.4ga6 适配笔记

## 编译环境
- 构建系统: autotools（suite3270 顶层 configure + 子组件 configure）
- 编译日期: 2026-08-28
- 编译器: clang 15.0.4（OHOS SDK 26.0.0.18，aarch64-linux-ohos）
- 状态: built

## 编译步骤

```bash
# 源码: https://github.com/pmattes/x3270/archive/refs/tags/4.4ga6.tar.gz
./configure --prefix=/storage/Users/currentUser/usr/local \
  --disable-x3270 --disable-tcl3270 \
  --disable-wc3270 --disable-ws3270 --disable-wb3270 --disable-wpr3287 \
  --disable-wx3270if --disable-wplayback --disable-wmitm --disable-windows-lib
make -j4
# 测试: python3 -m unittest discover（s3270/b3270/c3270/pr3287 各 Test 目录）
```

鸿蒙无 X11 环境，禁用 GUI 组件（x3270/wc3270 等）与 tcl3270，
仅构建命令行组件：s3270/b3270/c3270/pr3287/x3270if/playback/mitm/lib。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 无法识别 HarmonyOS | E007: 2018 版 config.guess 无 __OHOS__ 分支 | 用 automake 1.16 (2023) config.guess/config.sub 替换 + patch-autotools-ohos.pl 打补丁（补丁 0005/0006） |
| 2 | configure 报 config.status 临时目录 Permission denied | E011: HMDFS 下 umask 077 创建的 0700 目录不可写（UID 映射 20020082 vs 属主 20001006） | 所有 configure 脚本 umask 077→022（补丁 0001/0003-0004/0007-0024） |
| 3 | x3270if.c 报 struct termios/ECHO 未定义 | OHOS 下 ncurses.h 不间接引入 termios.h（glibc 有该行为） | x3270if.c 补 `#include <termios.h>`（补丁 0002） |
| 4 | 依赖头文件找不到 | AutotoolsToolchain 不注入依赖 cpp_info include 路径 | conanfile.py generate() 用 extra_cflags/extra_ldflags 注入 ncurses/readline/expat 路径 |
| 5 | out-of-source 构建失败（lib3270_files.mk 缺失） | x3270 顶层 Makefile 依赖源码树内相对路径，不支持 out-of-source | conanfile.py layout() 强制 in-tree 构建（folders.build="."） |

## 源码修改

24 个补丁（patches/0001-0024），分类：
- E007 平台识别：0005-config.guess.patch、0006-config.sub.patch
- E011 HMDFS 权限：0001、0003-0004、0007-0024（各 configure 脚本 umask 077→022）
- 平台编译修复：0002-Common-x3270if.c.patch（补 termios.h）

## 依赖版本

| 依赖 | 版本 | 用途 |
|------|------|------|
| ncurses | 6.6 | c3270 终端渲染（与 readline/8.3 依赖一致） |
| readline | 8.3 | c3270 命令行编辑 |
| expat | 2.8.2 | b3270 XML 解析 |

## 验证结果

```bash
# conan-verify 8 道门禁
G0 预构建评估 / G1 配方完整性 / G2 conan create / G3 系统同名库隔离
G4 产物完整性 / L2 smoke / L4 安全扫描 / L5 产物基线 → 全部通过

# 上游 Python unittest 集成测试（本地实测）
s3270: 232/253 (91.7%)  b3270: 72/74 (97.3%)  c3270: 4/18  pr3287: 12/12 (100%)
合计: 320/357 (89.6%)
# 失败均为平台/环境限制：c3270 需 pty 终端(headless 不可用)、
# HMDFS chmod 权限位不一致、无 /bin/bash、无 OpenSSL 头文件(TLS 禁用)
```

## 注意事项

- 鸿蒙无 X11：x3270（GUI）与 tcl3270 组件禁用，属预期裁剪
- TLS 未启用（configure 时无 OpenSSL 头文件），testTls 相关用例失败属环境限制
- c3270 为 curses 全屏程序，headless CI 无法运行其交互测试（Port not bound）
---

**编译结束**: 2026-08-28 02:50
**最终状态**: built
