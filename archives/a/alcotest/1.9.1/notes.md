# alcotest 1.9.1 适配笔记

## 编译环境
- 构建系统: custom (dune 3.17.0, OCaml 4.14.1)
- 编译日期: 2026-08-14
- 编译器: clang/clang++ (HarmonyOS toolchain)
- 状态: built

## 编译步骤

alcotest 是 OCaml 测试框架，不能使用标准 autotools/cmake 构建。采用以下步骤：

### 1. 编译 dune 3.17.0 (OCaml 构建系统)
```bash
# 下载 dune 源码
# Patch boot/libs.ml: 添加 "unix" 到 external_libraries
# Patch boot/duneboot.ml: 将 "threads" 改为 "threads.posix"
# Bootstrap 编译
ocaml boot/duneboot.ml
cp _boot/dune.exe ~/usr/local/bin/dune
```

### 2. 编译安装 OCaml 依赖
使用 ocamlc/ocamlopt 手动编译或 dune 编译以下库：
- seq, stdlib-shims, ocaml-syntax-shims, cppo
- astring, uutf, re, cmdliner
- fmt (含 fmt.tty, fmt.cli)

### 3. Monorepo workspace 方案编译 alcotest
```bash
# 创建 workspace，将 alcotest 和所有依赖源码放入同一目录
WS=~/tmp/alcotest-ws
# 子目录: astring, cmdliner, cppo, fmt, ocaml-syntax-shims, re, seq, stdlib-shims, uutf
# alcotest 源码: src/alcotest, src/alcotest-engine, src/alcotest-stdlib-ext

# 编译
dune build @install --root .
```

### 4. 打包
```bash
# 从 _build/install 复制到 staging 目录
cp -rL _build/install/default/lib/alcotest/ $STAGING/lib/alcotest/

# PackageBuilder 打包
# 生成 alcotest-1.9.1-ohos-aarch64.tar.gz (3982KB)
```

### 5. Conan 配方
```bash
conan create .
# test_package 验证 12 个关键文件全部通过
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | dune bootstrap 失败 | `threads` 库在 OHOS 上名为 `threads.posix` | patch duneboot.ml: `"threads"` → `"threads.posix"` |
| 2 | dune bootstrap 缺少 unix | OCaml 标准库 unix 未链接 | patch libs.ml: 添加 `"unix"` 到 external_libraries |
| 3 | dune 扫描父目录报 `/storage/Users: Operation not permitted` | HMDFS 权限限制 | 使用 `--root .` 避免向上扫描 |
| 4 | conan 包缓存中 .cmi/.mli 文件全是软链接不可读 | HMDFS (E050) 不支持跟踪符号链接 | 使用 monorepo workspace 方案，所有库从源码编译 |
| 5 | dune 无法发现外部库 (仅 META 文件不够) | dune 通过 dune-package 文件发现库，HMDFS 上不可读 | monorepo workspace 方案绕过外部库发现问题 |
| 6 | warning 50 (unexpected-docstring) 阻止编译 | fmt.mli 中有 unattached docstring | 删除 `| color (** deprecated *)` 中的 docstring |
| 7 | Cmdliner.Arg.env deprecated alert | 新版 cmdliner 弃用了 Arg.env 类型 | 在 fmt_cli dune 中添加 `(ocamlc_flags (:standard -alert -deprecated))` |
| 8 | dune env 块 flags 不生效 | bootstrap 编译的 dune 可能有 bug | 改用 per-library `ocamlc_flags`/`ocamlopt_flags` |
| 9 | alcotest 子包 (async/lwt/mirage/js) 依赖不可满足 | 需要 core_unix, lwt 等不在 workspace 中 | 只编译 alcotest 核心包，删除子包目录 |

## 依赖版本

| 依赖 | 版本 |
|------|------|
| OCaml | 4.14.1 (conan 包) |
| dune | 3.17.0 (源码编译) |
| astring | 0.8.5 |
| cmdliner | 1.3.0 |
| fmt | 0.9.0 |
| re | 1.12.0 |
| seq | 0.3.1 |
| stdlib-shims | 0.3.0 |
| uutf | 1.0.3 |
| ocaml-syntax-shims | 1.0.0 |

## 验证结果

```bash
# conan create 验证
alcotest/1.9.1 (test package): All 12 key files verified in package

# 关键产物
lib/alcotest/alcotest.cma       (110KB)
lib/alcotest/alcotest.cmxa      (2.3KB)
lib/alcotest/alcotest.a         (45KB)
lib/alcotest/engine/alcotest_engine.cma   (470KB)
lib/alcotest/engine/alcotest_engine.cmxa  (23KB)
lib/alcotest/engine/alcotest_engine.a     (476KB)
lib/alcotest/stdlib_ext/alcotest_stdlib_ext.cma   (62KB)
lib/alcotest/stdlib_ext/alcotest_stdlib_ext.cmxa  (805B)
lib/alcotest/stdlib_ext/alcotest_stdlib_ext.a     (29KB)
lib/alcotest/libalcotest_stubs.a  (12KB)
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| alcotest-1.9.1-ohos-aarch64.tar.gz | 3982KB | 主包 (bytecode + native + stubs) |
| alcotest-1.9.1-ohos-aarch64-debug.tar.gz | 300KB | 调试符号包 |

## 注意事项

- alcotest 是 OCaml 库，不是 C/C++ 库。conan 配方使用 `package_info()` 声明 .cma/.cmxa/.a 库文件，不含标准 C 头文件
- dune env 块的 `(flags ...)` 在 bootstrap 编译的 dune 中可能不生效，需使用 per-library `ocamlc_flags`
- HMDFS (E050) 软链接问题严重影响 OCaml 生态：标准库 .cmi、dune-package 文件等均为软链接
- `/tmp` 是只读文件系统，使用 `$HOME/tmp` 代替
- GitHub 直连超时，需使用 `gh-proxy.com` 镜像

## 上游 e2e 测试结果 (2026-08-14)

### Examples
- simple.exe: ✅ 4/4 tests passed
- floats.exe: ✅ 3/3 tests passed

### e2e/passing (23 tests)
- ✅ 19 tests: and_exit_false, and_exit_true, assert_and_verbose, assert_not_printed, basic, check_basic, cli_verbose, compact, empty_test_name, filter_name, filter_name_regex, isatty, match_raises, quick_only, quick_only_regex, separator_testname, skip_in_test, unicode_testname, verbose_newlines
- ✅ json_output (JSON format output: 3/0 success/failures)
- ✅ list_tests (lists test cases, not run mode)
- ✅ only_monadic_effects (no output, expected behavior)
- ✅ filter_range (需传入 CLI 参数 `test main 0..1,1-3,5`，传入后通过)

### e2e/failing (14 tests - all expected to fail with non-zero exit)
- ✅ All 14 tests exit non-zero as expected: bail, check_basic, check_located, check_long, compact, duplicate_test_names, empty_suite_name, exception_in_test, filter_all_tests, invalid_arg_in_test, long_test_case_name, outside_runner, tail_errors_limit, tail_errors_unlimited

### Summary: 39/39 tests pass (100%)

filter_range 需要传入 CLI 参数 `test main 0..1,1-3,5` 才能正确过滤测试用例。这是 dune e2e 测试框架的参数传递方式，不是 alcotest 库本身的缺陷。传入正确参数后 test-4 被正确 SKIP，测试全部通过。
