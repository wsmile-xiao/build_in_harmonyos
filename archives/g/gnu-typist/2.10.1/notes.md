# gnu-typist 2.10.1 适配笔记

## 编译环境
- 构建系统: Autotools
- 编译日期: 2026-08-16
- 编译器: OHOS clang 15
- 依赖: ncurses/6.6
- 状态: built

## 编译步骤
1. `conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing`
2. Autotools 构建流程: `configure` -> `make -j1` -> `make install`
3. configure 参数: `--disable-nls`
4. test_package 执行 `gtypist --version` 和 `gtypist --help`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `configure` 中 `mktemp -d` 在 HMDFS 上失败 | HMDFS 不支持该临时目录写入方式 | 在 build 阶段内联替换为 `mktemp -p` + `rm` + `mkdir` |
| 2 | `getopt.c` 因 `0` 作为空指针触发 clang 类型转换错误 | 旧版 getopt 实现与 clang 15 C99 检查不兼容 | 添加 `-Wno-int-conversion` |
| 3 | `gettext`/`_` 未定义 | OHOS libc 不提供 gettext，且本包禁用 NLS | 生成 `gettext_stub.h` 并通过 `-include` 注入 |
| 4 | `help2man`/`makeinfo` 缺失或 shebang 执行受限 | 目标环境没有这些文档工具，`/bin/sh` shebang 在旧端口不稳定 | 生成使用 `CONFIG_SHELL` shebang 的空 wrapper |
| 5 | 直接执行上游 `configure` 失败 | 构建目录脚本执行权限/解释器行为受限 | 显式通过 `CONFIG_SHELL` 运行 `configure` |
| 6 | `configure` 找不到 `ld` | 旧端口 profile 的 `CC` 是 shell-wrapped clang，Autoconf 不能可靠反推出 linker | 显式传入 `LD=ld.lld`, `AR=llvm-ar`, `RANLIB=llvm-ranlib` |
| 7 | `ncursesw/ncurses.h` 找不到 | `ncurses/6.6` 导出顶层 `ncurses.h`，上游检查宽字符子目录路径 | 生成 build-local `_compat_include/ncursesw/*.h` wrapper，并在 `CPPFLAGS` 前置 |

## 源码修改
未维护外部补丁文件，适配逻辑集中在 `conanfile.py`:
- 声明 `requires("ncurses/6.6")`
- 在 build 阶段内联修复 `configure` 的 `mktemp` 行为
- 为 `ncursesw/*.h` 生成兼容 include wrapper
- 通过 `CONFIG_SHELL` 运行 `configure`，并显式设置 `LD`/`AR`/`RANLIB`
- 生成 `help2man`、`makeinfo` 和 `gettext_stub.h`

## 验证结果

旧端口 `56267` 隔离 run:
`/storage/Users/currentUser/ohos-users/codex-a/gnu-typist-2.10.1-oldport-r1-20260816`

- r14: `L0/L1/L2/L4/L5` 全部通过
- `conan create` 成功
- `ncurses/6.6` 从 `ohpcd` 下载并作为 Conan 依赖消费
- test_package: 2/2 (`gtypist --version`, `gtypist --help`)
- 上游自动化测试: 0/0 (源码只有 Automake 默认空 `make check` 目标；未声明 `TESTS`、`check_PROGRAMS` 或 `check_SCRIPTS` 等测试用例)

```bash
$ gtypist --version
GNU Typist 2.10.1
```

```bash
$ gtypist --help
Usage: gtypist [OPTION...] [script-file]
```

## 交付物
- `conanfile.py`
- `conandata.yml`
- `manifest.yaml`
- `test_package/`

**编译结束**: 2026-08-16
**最终状态**: built
