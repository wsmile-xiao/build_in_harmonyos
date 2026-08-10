# aliddns c 适配笔记

## 编译环境
- 构建系统: makefile (raw Makefile, no ./configure)
- 编译日期: 2026-08-10
- 编译器: clang/clang++
- 状态: built

## 适配范围

上游 gghnicole/aliddns 是一个 OpenWrt/LEDE LuCI 软件包，主体是 shell
脚本（`usr/sbin/aliddns`）+ Lua 控制界面，依赖 OpenWrt SDK（`include $(TOPDIR)/rules.mk`
、`include $(INCLUDE_DIR)/package.mk`、`BuildPackage`），无法脱离 OpenWrt 环境独立构建。

本配方仅适配其中可移植的独立 C 工具 `tools/po2lmo`（PO → LMO 转换器，License
Apache-2.0）。po2lmo 是一个命令行工具，读入 gettext `.po` 文件，写出紧凑的
`.lmo` (Lua Machine Objects) 归档。其余 LuCI/shell 部分不在适配范围。

## 编译步骤

po2lmo 的 Makefile（`tools/po2lmo/Makefile`）非常简单：

```make
po2lmo: src/po2lmo.o src/template_lmo.o
	$(CC) $(LDFLAGS) -o src/po2lmo src/po2lmo.o src/template_lmo.o
```

依赖隐式规则 `.c.o:`（POSIX make 默认），因此必须在命令行显式传 `CC` 给 make。
配方在 `build()` 中用 `make -C tools/po2lmo -j1 CC=<clang> AR=<llvm-ar> RANLIB=<llvm-ranlib>`。
CC/AR/RANLIB 路径来自 Conan conf（R33），不从 shell 环境变量取。

产物 `tools/po2lmo/src/po2lmo` 是 ELF 可执行文件，`package()` 拷到 `bin/`。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游无 release tag | 仓库仅 1 次 commit (2020-04-17)，无 tag | 用 `archive/refs/heads/master.tar.gz` 作为源 |
| 2 | 上游是 OpenWrt 包不可独立构建 | Makefile `include $(INCLUDE_DIR)/package.mk` | 仅适配可移植的 tools/po2lmo C 子项目 |
| 3 | Makefile 无 `%.o:` 规则 | 依赖 POSIX make 隐式 `.c.o:` | build() 显式传 `CC` 给 make |

## 源码修改

无补丁。po2lmo 的 C 源仅依赖 libc + POSIX 头（fnmatch.h/sys/mman.h/dirent.h/
arpa/inet.h），OHOS/bionic 均提供，无需修改即可编译。

## 依赖版本

无外部依赖。

## 上游测试

上游源码、构建文件、发布包中均无任何测试套件（无 `make check`、无 `BUILD_TESTS`、
无 `test/` 目录、po2lmo 的 Makefile 无 test 目标）。MANIFEST.yml 据此声明
`upstream_tests_exist: false`。

## 验证结果

test_package 用一个真实的 `.po` 样本调用 `po2lmo input.po out.lmo`，再校验
输出 `.lmo` 非空且可被 po2lmo 自身的 round-trip 逻辑识别（读尾部 uint32 偏移）。

## 交付物

| 文件 | 说明 |
|------|------|
| `bin/po2lmo` | PO → LMO 转换工具（可执行） |

## 注意事项

- 版本号 `c` 取自积分赛任务标识，上游无语义化版本。
- 上游主仓库最后提交 sha: `1f9d0536ae6162c66e9fcf7c170da7663d954880` (2020-04-17)。
