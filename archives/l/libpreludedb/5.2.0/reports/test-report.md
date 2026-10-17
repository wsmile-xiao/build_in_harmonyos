# 测试报告 — libpreludedb 5.2.0（OHOS aarch64 / clang 15）

> 本报告数字全部来自实跑日志。下列日志为**本地一次性产物**（`reports/*.log` 不入库）：
> - `reports/w3-local-ci.log`：W3 本地 CI 模拟（含 L0/JC/KC/L1/L2/L4/L5 全门禁 + 44 项 make check 全量输出）
> - `reports/conan-create.log`：`conan-verify` 触发的干净 `conan create`（含 `make check` 全量输出）
> - `reports/conan-verify-report.md`：G0-G4 配方验证报告（本地一次性产物，不入库）
>
> 入库的测试证据：本文件 + `test_package/MANIFEST.yml`（上游测试声明，CI L0e）。

## 1. 上游测试（唯一上游测试入口）

| 项 | 值 |
|----|----|
| 命令 | `cd libmissing/tests && make check`（automake parallel-tests） |
| 说明 | 上游本包**没有**自己的 `tests/` 目录（`Makefile.am` 的 `SUBDIRS = m4 libmissing src plugins bindings docs`）；唯一 deterministic 入口是随树发布的 vendored gnulib 自检 `libmissing/tests` |
| 用例总数 | **44** |
| 通过 | **44** |
| 失败 | 0 |
| 跳过 | 0 |
| XFAIL / XPASS | 0 / 0 |
| ERROR | 0 |
| 通过率 | 100% (44/44) |

测试框架汇总行（实跑原文）：

```
Testsuite summary for libpreludedb 5.2.0
# TOTAL: 44
# PASS:  44
# SKIP:  0
# XFAIL: 0
# FAIL:  0
# ERROR: 0
```

用例清单（与 `libmissing/tests/Makefile.am` 的 `TESTS` 声明逐项一致，无增删/无跳过）：

```
test-alloca-opt  test-errno        test-fdopen        test-fgetc
test-float       test-fputc        test-fread         test-fwrite
test-intprops    test-inttypes     test-limits-h      test-rwlock1
test-lock        test-once1        test-once2         test-memchr
test-memrchr     test-pthread_sigmask1  test-pthread_sigmask2
test-raise       test-signal-h     test-sigprocmask   test-sleep
test-snprintf    test-stdalign     test-stdbool       test-stddef
test-stdint      test-stdio         test-stdlib        test-string
test-strnlen     test-sys_types    test-init.sh       test-thread_self
test-thread_create  test-time      test-unistd        test-usleep
test-vasnprintf  test-verify       test-verify.sh     test-vsnprintf
test-wchar
```

断言静态清点：`libmissing/tests/*.c`（50 个源文件）中 `ASSERT (` 共 **230** 处。

### 执行方式说明（两点，均未改动用例）

1. 必须在 `libmissing/tests` 目录内执行 `make check`：从父目录 `make -C libmissing/tests check`
   会让 libtool wrapper 的 getcwd 解析失败（HMDFS），44 项会**全部假失败**。
2. 本包**不需要** libprelude 那样的「有界重跑」：44 项在 OHOS 上稳定全绿（libprelude 的
   gnulib 自检有 3 项内核语义差异失败，本包 TESTS 声明即 44 项且无失败项）。

## 2. test_package（消费者 L1 测试，`conan create` 自动执行）

| 项 | 值 |
|----|----|
| 命令 | `./test_libpreludedb`（`conan create` 的 test_package 阶段） |
| 结果 | `libpreludedb 5.2.0 consumer test: OK`，退出码 0 |
| 覆盖 | ① `LIBPRELUDEDB_VERSION` 宏 + `preludedb_check_version()`（含「过高版本必须拒绝」的反向断言）；② `preludedb_selected_path_new_string()` 真实走 lex/yacc 生成的路径解析器（合法路径解析 + 非法路径必须报错）；③ libprelude 的 `idmef_message_new/destroy` 对象 API（验证 libpreludedb.so 的 DT_NEEDED 链在 OHOS 上可加载） |
| 断言数 | 9 条 CHECK |
| 日志 | `reports/conan-create.log`（`Running test()` 段） |

## 3. 本地门禁（W3 模拟 CI，等价 CI 的 prdiff 检查范围）

`reports/w3-local-ci.log` 中的最终结果：

| 门禁 | 结果 |
|------|------|
| L0m 目录结构（R39/L0m-4/L0m-5） | ✅ |
| KC 知识检查 | ✅ pass |
| JC 杂项文件（运行时状态/二进制/tarball/临时产物/隐藏文件白名单/单软件原子性） | ✅ pass（prdiff 模式，13 个文件） |
| L0 综合 | ✅ `pass: all checks passed` |
| L1（test_package 实跑 + 上游 make check + 破坏性反向验证） | ✅ `pass: upstream tests + test_package executed`（L1a/L1b/L1c/L1e 全部 ok） |
| L2 平台功能矩阵（smoke test） | ⏭️ `skip: no bin/ dir`（纯库包无 CLI，符合预期） |
| L4 静态安全扫描（补丁危险函数） | ✅ `pass: patches clean`（本包 0 补丁） |
| L5 产物基线 | ✅ `pass: lib/ has content` |
| Build Summary | Total 1 / Success 1 / Failed 0 / **Pass rate 100.0%** |

> W3 内同样实跑了上游 `make check`：`# TOTAL: 44 / # PASS: 44 / # SKIP: 0 / # FAIL: 0 / # ERROR: 0`
> （日志同文件，`Testsuite summary for libpreludedb 5.2.0`）。

> 注：W3 的 junk_check 以 `JUNK_PR_DIFF` 显式指定 PR 文件清单运行（等价 CI 的 `prdiff` 模式，
> 只检查本 PR 的 11 个文件），避免「整仓 full 模式」把 `origin/main` 里**他人**的既有运行态
> 文件（`archives/c/cloog/0.21.1/.build-closed` 等）算到本包头上。

## 4. 测试完整性声明（R51）

- 上游测试用例：**未减少、未跳过、未修改**。
- 源码补丁：**0 个**（`patches/` 为空）；测试相关源码未做任何改动。
- `test_package` 不能替代上游测试统计，故两者分别列出。
