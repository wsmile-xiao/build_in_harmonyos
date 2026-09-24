# imapfilter 2.8.3 适配笔记（aarch64-linux-ohos）

## 上游测试三步法申报（R51）

1. **清点**：上游 2.8.3 源码包无任何自动化测试套件。证据：
   - 全库 `find . -iname "*test*" -o -iname "check*"` 仅命中 `doc/`、`samples/`（无测试文件）
   - 顶层与 `src/` Makefile 均无 `check`/`test` 目标，无 make check
   - 非 cmake/meson 工程，无 ctest/pytest 注册（上游计数：tests/ 目录 0 个，注册用例 0 个）
2. **运行**：上游无测试可运行；按 R51 在 test_package 补齐 3 项消费者功能测试并在真机实测：
   - `imapfilter -V` → 输出 `IMAPFilter 2.8.3  Copyright (c) 2001-2025 Eleftherios Chatzimparmpas`，退出码 0 ✅
   - `imapfilter -h` → 打印 `usage: imapfilter [-inVv] [-c configfile] ...`，退出码 0 ✅
   - 包内 `share/imapfilter` 下 8 个 Lua 运行时模块齐全（test.sh 打包完整性检查）✅
   - 另做探索构建期人工冒烟：`./imapfilter -V` 同上通过。
3. **回填**：上游实测 0/0（上游确无测试，见清点证据）；补齐测试实测 3/3，通过率 100%。

## 构建过程

- 构建系统：裸递归 Makefile（顶层 Makefile → src/Makefile），无 configure。
- 依赖（均来自 ohpcd 制品仓，静态包）：lua/5.4.8.1、pcre2/10.48、openssl/3.5.8.1。
- 探索编译：`make CC=clang INCDIRS='-I<dep>/include ...' LIBDIRS='-L<dep>/lib ...'`
  一次通过（编译 0 警告错误、链接成功）。
- **无需任何源码补丁**：代码为可移植 POSIX C；OHOS clang 15 下 -Wall -Wextra 干净通过。
- Makefile 中硬编码的 SSLCAPATH/SSLCAFILE（/etc/ssl/...）仅编译期默认值，
  运行时由 Lua 配置指定 trust store，不影响打包。

## 配方要点

- package_type = application；包产物：bin/imapfilter + share/imapfilter/*.lua。
- build() 中编译器取自 `tools.build:compiler_executables:c`（R33），
  依赖目录取自 `self.dependencies` 依赖图（R49），不依赖 shell 环境变量。
- R38：CLI 工具，软件级 commands.json 已声明。
- 上游无 conanfile，源 URL 为官方 GitHub releases（R39/PF7）。
---

**编译结束**: 2026-09-21 07:49
**最终状态**: built
