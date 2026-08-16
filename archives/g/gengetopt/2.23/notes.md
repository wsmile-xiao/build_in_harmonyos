# gengetopt 2.23 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-06-09
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. **源码下载**: https://ftp.gnu.org/gnu/gengetopt/gengetopt-2.23.tar.xz
2. **初始化**: ohc-run.py init-build gengetopt 2.23
3. **平台适配**:
   - 修改 build-aux/config.guess 添加 HarmonyOS 检测
   - 修改 build-aux/config.sub 添加 linux-ohos 支持
4. **配置**: 使用 autoreconf -fvi 重新生成 configure
5. **编译**: 在独立 build 目录执行 make（autotools VPATH 构建）
6. **安装**: make install DESTDIR=$TEST_PREFIX
7. **打包**: ohc-run.py package gengetopt 2.23

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 无法识别 HarmonyOS | 缺少 HarmonyOS case 分支 | 手动添加 `*:HarmonyOS:*:*)` case，输出 aarch64-unknown-linux-ohos |
| 2 | config.sub 不识别 linux-ohos | OS 列表中缺少 ohos | 在两处添加 `linux-ohos*` 支持（maybe_os case + OS 列表） |
| 3 | config.status 无法创建临时目录 | HMDFS 权限问题（所有者 UID != 运行用户 UID） | 使用 autotools VPATH 构建（在独立目录运行 configure） |
| 4 | PACKAGE/VERSION 未定义 | 现代 autoconf 默认不定义旧宏 | 手动编辑 build 目录的 config.h，添加 PACKAGE="gengetopt" 和 VERSION="2.23" |
| 5 | help2man 缺失导致文档生成失败 | 构建工具缺失 | 二进制已编译成功，跳过文档生成（不影响核心功能） |

## 源码修改

### build-aux/config.guess
- 添加 HarmonyOS 系统识别：第166行插入 `*:HarmonyOS:*:*)` case 分支
- 输出三元组：`aarch64-unknown-linux-ohos`

### build-aux/config.sub
- 第118行：在 maybe_os case 添加 `linux-ohos*`
- 第1383行：在 OS 列表添加 `-linux-ohos*`

### config.h（build 目录）
- 定义 PACKAGE="gengetopt"
- 定义 PACKAGE_NAME="GNU gengetopt"
- 定义 PACKAGE_STRING="GNU gengetopt 2.23"
- 定义 PACKAGE_TARNAME="gengetopt"
- 定义 PACKAGE_VERSION="2.23"
- 定义 VERSION="2.23"

## 依赖版本

- clang 15.0.4
- autoconf 2.72
- automake 1.16.5
- libtool 2.4.7
- flex (系统版本)
- bison (系统版本)

## 验证结果

```bash
$ gengetopt --version
GNU gengetopt 2.23
Copyright (C) 1999-2011  Free Software Foundation Inc.
This program comes with ABSOLUTELY NO WARRANTY; for details
please see the file 'COPYING' supplied with the source code.
This is free software, and you are welcome to redistribute it
under certain conditions; again, see 'COPYING' for details.
This program is released under the GNU General Public License.
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| gengetopt-2.23-ohos-aarch64.tar.gz | 651KB | 预编译包（已 strip） |
| gengetopt-2.23-ohos-aarch64-debug.tar.gz | 4.0MB | 调试包（含符号表） |

## 注意事项

1. **VPATH 构建**: 由于 HMDFS 权限问题，必须在独立 build 目录运行 configure
2. **PACKAGE/VERSION**: 现代 autoconf 需手动定义，否则生成的 cmdline.c 会编译失败
3. **help2man**: 非必需，不影响核心二进制编译

---
**编译结束**: 2026-06-09 10:55
**最终状态**: built

---

## 补充：鸿蒙 PC conan 配方（2026-08-17）

# gengetopt 2.23 编译笔记（HarmonyOS PC · conan / autotools）
## 定位
命令行选项解析器生成器 — 读 .ggo 描述文件，生成 cmdline.c/cmdline.h
产出命令行工具：`gengetopt`。

## 源码
- URL：https://ftp.gnu.org/gnu/gengetopt/gengetopt-2.23.tar.xz
- sha256：`b941aec9011864978dd7fdeb052b1943535824169d2aa2b0e7eae9ab807584ac`

## 关键适配

- **设备上没有 texinfo**：只要 automake 项目去建 .info，`missing` 脚本报 `makeinfo: command not found` → Error 127。统一 `MAKEINFO=true` 跳过
- 只建 src/ 这件事换了三种写法才对：`make -C src` 会崩 libtool（HMDFS 上 `getcwd: cannot access parent directories`，接着报 `ignoring unknown tag CXX`）；`make SUBDIRS=src` 命令行变量会**递归传进子 make**，src/Makefile 拿着它再去 cd src；最终改 configure 生成的**顶层 Makefile 的 SUBDIRS 行**为 `gl src` —— gl 是 gnulib，`src/libgengetopt.la` 依赖 `../gl/libgnu.la`，丢不得
- 删除 `lib/*.la`：里面烤死 libdir 绝对路径（conan 按 prefix=/ 构建 → 写的是 `/lib`），下游 libtool 会去找 `//lib/libxxx.la` 而失败
- 修 configure 的 `umask 077` → `022`（HMDFS 上 077 会让后续步骤读不到自己刚建的临时文件）

## 真机验证（2026-08-17）

设备：HUAWEI MateBook（HAD-W32 / 2in1），OHOS aarch64。
`conan create . -pr ohos-native` 通过，test_package 断言：

1. 喂一份最小 .ggo 真跑一遍生成，断言 cmdline.h 有 struct gengetopt_args_info、cmdline.c 有 cmdline_parser 实现、声明的选项字段确实出现在生成物里 ✅

> 这个包一共重跑了 5 轮才通过，每轮换一个不同的真因（详见上面「关键适配」）。

## 状态

built —— 真机已验证；制品**尚未上传**（上传须单独过闸）。

