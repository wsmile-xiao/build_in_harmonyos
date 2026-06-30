# nettoe 1.5.1 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-06-29
- 编译器: clang 15.0.4 / clang++
- 平台: aarch64-unknown-linux-ohos (HarmonyOS)
- 状态: published

## 编译步骤

```bash
# 1. 初始化 (init-build 自动下载源码)
python3 ohc-run.py init-build nettoe 1.5.1 --url=https://downloads.sourceforge.net/project/nettoe/nettoe/1.5.1/nettoe-1.5.1.tar.gz

# 2. 进入源码目录
source .build-context-nettoe-1.5.1
cd $BUILD_SRC_DIR

# 3. 更新 config.guess/config.sub (E007)
cp /storage/Users/currentUser/usr/local/share/automake-1.17/config.guess build-aux/config.guess
cp /storage/Users/currentUser/usr/local/share/automake-1.17/config.sub build-aux/config.sub

# 4. 修复 configure 中 umask 077 → 022
sed -i 's/umask 077/umask 022/g' configure

# 5. 修复 game.h 重复符号: int → extern int
# 6. 在 nettoe.c 中添加变量定义

# 7. 编译 (R1: 参数最少化)
umask 022
./configure --prefix=$DEFAULT_PREFIX
make -j2

# 8. Staging 安装
make install DESTDIR=$TEST_PREFIX

# 9. 测试
make check
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure: error: cannot guess build type | config.guess (2012) 不识别 HarmonyOS (E007) | 从 automake 1.17 复制 2023 版 config.guess/config.sub |
| 2 | config.status: Permission denied (subs1.awk) | umask 077 创建的目录在 HarmonyOS 上无法写入文件 | 修改 configure 中 umask 077 → 022 |
| 3 | ld.lld: error: duplicate symbol: NO_COLORS/NO_BEEP/addrfamily | game.h 中 int 定义 (非 extern) 被多个 .c 文件包含 | game.h 改为 extern 声明，nettoe.c 中添加定义 |

## 源码修改

| 文件 | 修改内容 |
|------|----------|
| build-aux/config.guess | 替换为 automake 1.17 版本 (2023)，支持 HarmonyOS 检测 |
| build-aux/config.sub | 替换为 automake 1.17 版本 (2023)，支持 aarch64-unknown-linux-ohos |
| configure | umask 077 → umask 022 (2处) |
| src/game.h | `int NO_BEEP;` → `extern int NO_BEEP;` (3个变量) |
| src/nettoe.c | 添加 `int NO_BEEP = 0; int NO_COLORS = 0; int addrfamily = 0;` |

## 依赖版本

- clang 15.0.4
- ncurses (系统静态库 libncurses.a, 链接为 libncursesw.a)
- musl libc (系统共享库 libc.so)
- 无外部 Conan 依赖

## 验证结果

```bash
# make check
PASS: terminfo
=============
1 test passed
=============

# nettoe --version
netToe 1.5.1 (March 21th, 2014) with terminfo support, at TCP port 7501.

# readelf -d (R26 静态链接验证)
NEEDED: Shared library: [libc.so]  # 仅系统库，ncurses 已静态链接

# conan-verify 8 道门禁
G0 PASS | G1 PASS | G2 PASS | G3 PASS | G4 PASS | L2 PASS | L4 PASS | L5 PASS
```

## 注意事项

- HarmonyOS 上 umask 077 会导致目录内文件创建失败 (HMDFS/MAC 限制)，所有 autotools 项目需注意
- nettoe 是终端工具，ncurses 仅静态库可用，自动满足 R26 静态链接要求
- config.guess/config.sub 版本过旧 (2012) 是所有 autotools 项目的第一道门槛 (E007)
---

**编译结束**: 2026-06-30 16:33
**最终状态**: published
