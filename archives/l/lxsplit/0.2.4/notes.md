# lxsplit 0.2.4 适配笔记

## 编译环境
- 构建系统: makefile（简单 GNU Makefile，非 autotools，无 configure 脚本）
- 编译日期: 2026-08-26
- 编译器: clang 15（来自 OHOS Conan profile `tools.build:compiler_executables`）
- 平台: OpenHarmony aarch64 (musl libc)
- 状态: built

## 源码核实

- **上游**: https://lxsplit.sourceforge.net/
- **源 URL**: `https://downloads.sourceforge.net/project/lxsplit/lxsplit/0.2.4/lxsplit-0.2.4.tar.gz`
- **SHA256**: `858fa939803b2eba97ccc5ec57011c4f4b613ff299abbdc51e2f921016845056`
  - 与 Ubuntu/Debian `lxsplit_0.2.4.orig.tar.gz`、SlackBuilds、debian-multimedia .dsc 一致
  - MD5: `ed21a08c167c08d4d81c820782947cb1`（与各发行版一致）
- **许可证**: GPL-2.0-or-later
  - COPYING 文件为 GNU GPL v2 全文
  - 源码头部（config.h/main.c/split.c/merge.c/func.c）均声明 "version 2 of the License, or (at your option) any later version"
- **作者**: Richard Stellingwerff（原作者），O. Sezer（维护者）
- 源码包内容（14 项）：Makefile, config.h, func.c/h, merge.c/h, split.c/h, main.c, mkuoff_t.c, README, ChangeLog, COPYING, lxsplit.spec

## 编译步骤

1. **下载源码**: Conan `tools.files.get()` 从 conandata.yml 的 URL 下载并校验 SHA256。

2. **编译**: `make CC=<ohos-clang> -j1`
   - CC 来自 Conan conf `tools.build:compiler_executables`（R33 铁律：禁止用 shell `${CC}`）
   - Makefile 默认 `CFLAGS ?= -O2`，追加 `-Wall -W -DNO_DEBUG`
   - LFS 默认开启：`-D_LARGEFILE_SOURCE -D_LARGEFILE64_SOURCE -D_FILE_OFFSET_BITS=64`
   - 产物: `lxsplit`（ELF aarch64）

3. **打包**: `copy("lxsplit", build_folder → package/bin)`
   - 产物结构: `bin/lxsplit`（CLI 工具，非 library）

4. **make check**: 跳过（Makefile 无 test/check 目标）

## 零补丁说明

上游 Makefile 的注释写道：
> FIXME: This makefile is NOT suitable for cross-compiling,
> because we are generating uoff_t.h during compilation..

原因：`mkuoff_t.c` 被编译为 `mkuoff_t` 并在构建期运行以生成 `uoff_t.h`（探测 `sizeof(long)` / `sizeof(off_t)`）。传统交叉编译（x86 host → aarch64 target）下，构建出的 `mkuoff_t` 无法在 host 运行。

但 **OHOS Conan profile 的 build = host = target = aarch64**（profile 同时用作 `-pr:b` 和 `-pr:h`，参见 lavat 适配笔记 "Platform: OpenHarmony aarch64 (musl libc)"）。构建在目标架构上原生进行，`mkuoff_t` 直接运行，无交叉运行问题。因此**零补丁**即可完成。

## 功能测试

test_package 做真实端到端测试（非仅 `--help`）：
1. 创建一个临时小文件（含可识别内容）
2. 调用 package 中的 `lxsplit -s <file> 1k` 分割
3. 调用 `lxsplit -j <file>.001` 合并
4. 用 `cmp` 对比恢复文件与原文件内容
5. 检查返回码与内容一致性

- test 必须使用 Conan package 中的 `bin/lxsplit`（通过 `self.dependencies["lxsplit"].package_folder` 取绝对路径，禁止系统 lxsplit）
- 输出文件命名：split → `<basename>.001/.002...`；join 输入需 `.001` 结尾，输出为去掉 `.00x` 的原名

## 依赖

无外部依赖。lxsplit 是纯 C 程序，仅依赖 musl libc。

## 注意事项

- lxsplit 是 CLI 工具（split/join），`package_type = "application"`，不应封装为 library
- split 输出在当前工作目录，test_package 需用临时目录隔离
- 上游无 make check，功能验证依赖 test_package 的 split→join→cmp 流程
