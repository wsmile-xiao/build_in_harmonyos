# progress 0.17 适配笔记

## 编译环境
- 构建系统: makefile（纯 Makefile 项目，无 configure 脚本）
- 编译日期: 2026-06-01
- 编译器: clang/clang++
- 状态: published

## 编译步骤

progress 是纯 Makefile 项目，无 configure/configure.ac/CMakeLists.txt，直接使用 make 编译。

```bash
# 1. 下载源码（ohc-run.py init-build 自动完成）
# 2. 检查源码结构：仅 Makefile，无 configure
# 3. 编译
cd $BUILD_SRC_DIR
make clean
make PREFIX=$DEFAULT_PREFIX CC=clang CFLAGS="-fPIC -O2 -Wall -D_FILE_OFFSET_BITS=64" LDFLAGS="-lm -L$DEFAULT_PREFIX/lib -lncursesw" -j1

# 4. Staging 安装（DESTDIR 模式）
make install DESTDIR=$TEST_PREFIX PREFIX=$DEFAULT_PREFIX

# 5. 预编译包制作
python3 $SKILL_ROOT/scripts/ohc-run.py package progress 0.17

# 6. 本地安装验证
make install PREFIX=$DEFAULT_PREFIX
$DEFAULT_PREFIX/bin/progress --version  # 输出: progress version 0.17
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 构建系统标注为 autotools | init-build 默认标注为 autotools | 实际为纯 Makefile 项目，修正 build_system 为 makefile |
| 2 | manifest.yaml 缺少顶级 build_system 字段 | 模板未包含此字段 | 手动添加 build_system: makefile |
| 3 | manifest.yaml sha256 为空 | 模板占位符未填充 | 计算 tarball sha256 并填入 |
| 4 | notes.md 使用模板占位符 | 重做前未填充实际内容 | 替换为实际编译记录 |
| 5 | G0 clean-verify 失败：无 configure 脚本 | progress 是纯 Makefile 项目 | 添加 0002-configure.patch（configure wrapper，no-op） |
| 6 | G0 clean-verify 失败：make 找不到 curses.h | Makefile PREFIX 定义位置在 HarmonyOS 分支之后，且默认为 /usr/local | 添加 0001-Makefile.patch：将 PREFIX/DEFAULT_PREFIX 定义移至开头，使用 DEFAULT_PREFIX 环境变量 |

## 源码修改

### 补丁 1: 0001-Makefile.patch
- **类型**: 平台适配 (platform_adaptation)
- **内容**: 将 `PREFIX ?= /usr/local` 定义移至 Makefile 开头，添加 `DEFAULT_PREFIX ?= /usr/local; PREFIX ?= $(DEFAULT_PREFIX)` 使 HarmonyOS 分支能正确读取环境变量中的安装路径
- **原因**: 原始 Makefile 的 PREFIX 定义在 HarmonyOS 条件分支之后（第27行），导致 clean-verify 中 PREFIX 为空值；DEFAULT_PREFIX 环境变量（由构建系统设置）需要被 Makefile 使用才能找到 ncurses 头文件

### 补丁 2: 0002-configure.patch
- **类型**: 平台适配 (platform_adaptation)
- **内容**: 添加 configure wrapper 脚本，为纯 Makefile 项目提供 no-op configure 接口
- **原因**: clean-verify 管线要求运行 configure 步骤，但 progress 没有 configure 脚本

## 依赖版本

- ncurses/6.5（静态库 libncursesw.a，已预编译安装）

## 验证结果

```bash
$ progress --version
progress version 0.17

$ progress -h
progress - Coreutils Viewer
Shows progress on file manipulations (cp, mv, dd, ...)

$ file /storage/Users/currentUser/usr/local/bin/progress
progress: ELF shared object, 64-bit LSB arm64, dynamic (/lib/ld-musl-aarch64.so.1), not stripped
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| progress-0.17-ohos-aarch64.tar.gz | 328777 bytes | 预编译包 |
| progress-0.17-ohos-aarch64-debug.tar.gz | 78881 bytes | 调试符号包 |
| progress (binary) | 272832 bytes | 二进制文件 |

## 注意事项

- progress 是纯 Makefile 项目，不支持 make check（无测试套件）
- Makefile 的 HarmonyOS 分支通过 `-I$(PREFIX)/include` 和 `-L$(PREFIX)/lib -lncursesw` 链接 ncursesw
- 编译时必须传递 PREFIX=$DEFAULT_PREFIX，否则安装路径不正确
- Makefile 的 PREFIX 定义必须位于 HarmonyOS 条件分支之前，否则 clean-verify 中 PREFIX 为空
- G0 clean-verify 需要两个补丁：0001-Makefile.patch（PREFIX 定义位置）和 0002-configure.patch（configure wrapper）

---

**编译结束**: 2026-06-01
**最终状态**: published
