# e2fsimage 0.2.3 编译笔记

## 编译日期
2026-06-03

## 编译环境
- 系统: HarmonyOS (HongMeng Kernel 1.12.0)
- 编译器: clang (LLVM from OHOS SDK)
- 链接器: ld.lld (LLVM from OHOS SDK)
- 构建系统: makefile (custom shell configure renamed to configure.custom)

## 依赖
- e2fsprogs 1.47 ✅ (libext2fs.a, libcom_err.a, libe2p.a — prebuilt static libraries)

## 问题与解决

### 问题1: configure 脚本 `cd --` 不兼容 zsh
**原因**: zsh 不支持 `cd --` 作为选项分隔符。
**解决**: 将 configure 重命名为 configure.custom；修改 `cd --` 为 `cd "$dir"`；添加 `case "$dir" in --*) continue` 跳过 --prefix 参数。

### 问题2: configure 使用 gcc 但只有 clang 可用
**原因**: HarmonyOS 系统没有 gcc。
**解决**: 在 configure 和 Local.mak 中将 gcc→clang，设置 CC=${CC:=clang}。

### 问题3: VPATH 构建失败（无 Makefile 在 build dir）
**原因**: e2fsimage 的 Makefile 不支持 VPATH 构建；Build driver 创建独立 build 目录用于 autotools。
**解决**: 重命名 configure 以绕过 autotools 检测；将构建系统改为 "makefile"。

### 问题4: 缺少 ext2fs/ext2fs.h 头文件
**原因**: 预编译的 e2fsprogs 只包含 ext2_fs.h 和 ext2_types.h。
**解决**: 创建兼容性头文件 ~/usr/local/include/ext2fs/ext2fs.h，包含类型定义、函数原型和宏定义。使用 #undef/#define 覆盖 ext2_fs.h 中不匹配的宏。

### 问题5: EXT2_ET_DIR_NO_SPACE 未定义
**原因**: ext2_err.h 未包含在预编译 e2fsprogs 中。
**解决**: 在 ext2fs.h 中添加 EXT2_ET_BASE 和 EXT2_ET_DIR_NO_SPACE 定义。

### 问题6: `install` 命令不可用
**原因**: HarmonyOS 没有 GNU coreutils install 命令。
**解决**: 修改 src/Makefile 和 man/Makefile 中的 install 目标，使用 mkdir + cp + chmod 替代。

### 问题7: Local.mak 被 distclean 删除
**原因**: Build driver 在 configure 前运行 make distclean，删除了预创建的 Local.mak。
**解决**: 从 Makefile 中移除 Local.mak:configure 依赖和 distclean 中 Local.mak 的删除规则。

## 补丁文件
- 0001-Local.mak.patch (新增预创建配置文件 CC=clang, VERSION=0.2.3)
- 0002-Makefile.patch (移除 Local.mak:configure 依赖和 distclean 删除)
- 0003-configure.custom.patch (gcc→clang, zsh 兼容, 跳过 --prefix, 交叉编译安全)
- 0004-man-Makefile.patch (install→mkdir+cp)
- 0005-src-Makefile.patch (install→mkdir+cp+chmod)

## 功能验证
- ✅ e2fsimage 二进制编译成功
- ✅ ELF shared object, 64-bit LSB arm64, dynamic

## 交付物
- e2fsimage-0.2.3-ohos-aarch64.tar.gz (265791 bytes, stripped binary package)
- e2fsimage-0.2.3-ohos-aarch64-debug.tar.gz (329801 bytes, debug symbols package)

**编译结束**: 2026-06-03 17:49
**最终状态**: built
---

**编译结束**: 2026-08-06 09:11
**最终状态**: published
