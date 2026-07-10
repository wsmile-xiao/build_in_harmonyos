# adr-tools 3.0.0 适配笔记

## 编译环境
- 构建系统: 无（纯 Shell 脚本项目，make install 仅复制文件）
- 编译日期: 2026-07-02
- 编译器: N/A（无编译步骤）
- 状态: published

## 编译步骤

adr-tools 是纯 Bash 脚本项目，无需编译。"安装"即将 src/ 目录下的脚本复制到 bin/ 目录。

1. 下载源码包（GitHub SSL 超时，使用 ghfast.top 镜像下载）
2. 解压源码
3. 修复 shebang：所有 src/ 脚本的 `#!/bin/bash` → `#!/usr/bin/env bash`
4. 修复 cat heredoc 兼容性问题（见下方问题表）
5. 复制 src/* 到 $TEST_PREFIX/bin/
6. 运行 `make check` 验证功能（22 项测试全部通过）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `/bin/bash` 不存在 | OHOS 无 /bin/bash，bash 安装在 /usr/local/bin | 修改所有脚本 shebang: `#!/bin/bash` → `#!/usr/bin/env bash` |
| 2 | `cat <<EOF` 报 "Broken pipe" 退出码 1 | GNU coreutils cat 在 OHOS 上从 heredoc stdin 读取时返回非零退出码 | `_adr_generate_toc`: 用 `echo` 替换 heredoc; `_adr_help_new`: 添加 `|| true` |
| 3 | Makefile BUILDDIR 硬编码 /tmp | /tmp 在 OHOS 上只读 | 修改 BUILDDIR 使用 $TMPDIR |
| 4 | Makefile PATH 不含 bash | 测试 PATH 只含 /bin:/usr/bin | 添加 $DEFAULT_PREFIX/bin 到 PATH |
| 5 | `getopt` 不在默认 PATH | getopt 安装在 harmonybrew 目录 | 添加 harmonybrew/bin 到测试 PATH |
| 6 | GitHub SSL 证书验证失败 | OHOS CA 证书问题 | 使用 ghfast.top 镜像下载到 $TMPDIR |

## 源码修改

所有修改在 conanfile.py 的 `build()` 方法中动态完成，无需补丁文件。

修改的源文件（运行时由 conanfile.py 自动修复）：
- `src/_adr_add_link` 等 22 个脚本: shebang 修复
- `src/_adr_generate_toc`: cat heredoc → echo
- `src/_adr_help_new`: cat heredoc 添加 `|| true`

Makefile 修改（仅用于测试，不影响打包）：
- BUILDDIR: `/tmp/adr-tools-build` → `$(if $(TMPDIR),$(TMPDIR),/tmp)/adr-tools-build`
- PATH: 添加 `$(DEFAULT_PREFIX)/bin` 前缀
- clean: `/tmp/adr-tools-build` → `$(BUILDDIR)`

## 依赖版本

无编译依赖。运行时需要 bash（由系统提供或 conan 依赖）。

## 验证结果

```bash
# 功能测试
$ adr init doc/adr
doc/adr/0001-record-architecture-decisions.md
$ adr new "Use ADR format"
doc/adr/0002-use-adr-format.md
$ adr list
doc/adr/0001-record-architecture-decisions.md
doc/adr/0002-use-adr-format.md

# 上游测试套件
$ make DEFAULT_PREFIX=$DEFAULT_PREFIX check
TEST: alternative-adr-directory
TEST: autocomplete
TEST: avoid-octal-numbers
TEST: create-first-record
TEST: create-mutiple-records
TEST: edit-adr-on-creation
TEST: funny-characters
TEST: generate-contents-with-header-and-footer
TEST: generate-contents-with-prefix
TEST: generate-contents
TEST: generate-graph
TEST: init-adr-repository
TEST: linking-new-records
TEST: linking
TEST: list-records
TEST: migrate-date-format
TEST: must-provide-a-title-when-creating-new-adr
TEST: project-specific-template
TEST: search-for-adr-dir
TEST: search-for-custom-adr-dir
TEST: supercede-existing-adr
TEST: supercede-multiple-adrs
SUCCESS
```

## 注意事项

1. 本包为纯脚本包，无二进制文件，无需静态链接（R26 不适用）
2. settings 仅声明 "os" 和 "arch"，不需要 "compiler" 和 "build_type"
3. package_info 设置 bindirs=["bin"]，libs=[]（无库文件）
4. R32: settings.os 判断在运行时隐式处理（脚本通过 /usr/bin/env bash 自动适配）
---

**编译结束**: 2026-07-02 11:53
**最终状态**: published
