# mailcheck 1.91.2 适配笔记

## 上游信息

- **名称**: mailcheck
- **版本**: 1.91.2
- **主页**: https://mailcheck.sourceforge.net/
- **源码**: https://downloads.sourceforge.net/project/mailcheck/mailcheck/1.91.2/mailcheck_1.91.2.tar.gz
- **SHA256**: 6ca6da5c9f8cc2361d4b64226c7d9486ff0962602c321fc85b724babbbfa0a5c
- **许可证**: GPL-2.0-or-later (COPYING 文件为 GPL v2 全文)

## 上游测试

**无上游测试**。Makefile 仅定义 `all/debug/mailcheck/install/distclean/clean`
目标，无 `check`/`test` 目标。tarball 内无 `tests/` 目录、无 `configure` 脚本、
无 CI 配置。SourceForge 项目页亦未提供测试说明。

证据：
- `tar tzf mailcheck_1.91.2.tar.gz` 列出的 7 个文件中无任何 test/check 文件
- Makefile 内容：`all: mailcheck` / `debug:` / `mailcheck:` / `install:` / `distclean:` / `clean:`
- 无 `configure` 脚本（不是 autotools 项目）
- 无 `.travis.yml` / `.github/workflows/` 等 CI 配置

## 构建方式

plain Makefile，无 configure。直接 `make CC=<clang>` 即可编译。
Makefile 硬编码 `-Wall -O2` 和 `-s`（strip）标志，CC 是唯一可覆盖变量。

## 适配要点

1. 使用 Conan conf `tools.build:compiler_executables[c]` 获取 clang 路径（R33），
   不裸用 shell `${CC}` 变量。
2. 仅传递 `CC=<clang>` 给 make，不传 CFLAGS（Makefile 不使用 `$(CFLAGS)` 变量）。
3. 无外部库依赖，纯 C 标准库（socket、netdb、dirent 等均为 OHOS 标准头文件）。
4. 无需补丁，源码直接编译通过。

## test_package

包级补充测试（非上游测试）：创建真实 mbox 文件和 .mailcheckrc，
运行 mailcheck 二进制，验证输出包含 "mail in" 和 mbox 路径。
共 3 个断言（exit code、输出内容、路径匹配）。
