# 上游测试真机执行报告 — john-jumbo 1.9.0

## 结论

| 项 | 值 |
|---|---|
| 上游测试目标 | `src/Makefile.legacy` 的 `unit-tests:`（tests/unit-tests.c，官方随发行 tarball 分发） |
| 执行环境 | OHOS 真机（192.168.43.14，conan 2.29.1，clang 15.0.4 aarch64-unknown-linux-ohos） |
| 测试函数 | 37 / 37 全部通过 |
| 用例计数 | 43,067,484 次检查全部通过（逐用例计数） |
| 退出码 | 0 |
| 耗时 | 4.60s |

> R51 三步法：清点 → 实跑 → 如实回填。上游随发行 tarball 的正式测试入口有两条：
> (1) `test:` 目标 → `cd ../test && perl jtrts.pl -q`（John Test Suite）：**发行 tarball
> 不含 test/ 目录**（jtrts 为独立仓库；git tag 1.9.0-Jumbo-1 递归计数同样无 test/ 目录，
> `src/tests/` 共 24 个文件 = unit-tests.c + NESSIE 11 + NIST_CAVS 12 向量数据），且
> OHOS 设备无 perl → 平台受限（RESTRICTED），无法执行；
> (2) `unit-tests:` 目标（tests/unit-tests.c + misc.c/common.c/memory.c/sha2.c，
> 纯 C、无外部运行时依赖）→ **真机全量执行通过**（本报告）。
>
> 另：--test 内置自检向量（NESSIE/NIST_CAVS 编译进二进制）由消费者探针 T4 承接覆盖。

## 执行命令与产物

```sh
cd <source_folder>/src
CPATH=<openssl-package>/include \
  make -f Makefile.legacy unit-tests CC=clang
```

复现脚本：`bash reports/run-upstream-tests.sh <john-source-folder> [cc]`（固化下述三处
环境适配，真机实测、幂等、测试逻辑零改动）。

## 环境适配（3 处，均不涉及测试逻辑改动）

上游目标为 Linux 假设编写，在 OHOS 上执行需三处环境适配，测试逻辑零改动：

1. **编译期 openssl 头文件**：unit-tests 目标硬编码 `-Wall -O2 -fomit-frame-pointer`
   （不使用 $(CFLAGS)），而 sha2.h 包含 `<openssl/opensslv.h>` → 经 `CPATH` 注入
   conan 依赖 openssl/1.1.1w 的 include 目录。
2. **临时文件路径**：`_nontest_gen_fgetl_files()` 硬编码 `/tmp/jnk*.txt` 三个临时
   文件；OHOS /tmp 只读（E002）→ 以 `sed 's|/tmp/jnk|./ut-jnk|g'` 重定向到 cwd
   （其余 12 处引用全部为这三个文件的建/删/读，逐一对应，无其它改动）。
3. **运行 cwd**：sha2 测试数据 `tests/NIST_CAVS/*.rsp` 为相对路径 → 从 src/
   目录执行（cwd 缺数据文件时上游会先报 "Unable to open testing file" 并崩溃——
   上游对数据缺失无防护，见下）。

## 完整输出

```
**** Performing unit tests for functions from [misc.c] ****
  test 1 _nontest_gen_fgetl_files -  Performed        3 tests 0.16 seconds used
  test 2 test_fgetl               -  Performed    18003 tests 0.47 seconds used
  test 3 test_fgetll              -  Performed    18003 tests 0.32 seconds used
  test 4 test_strncpy_pad         -  Performed       27 tests 0.00 seconds used
  test 5 test_strnfcpy            -  Performed       27 tests 0.00 seconds used
  test 6 test_strnzcpy            -  Performed       27 tests 0.00 seconds used
  test 7 test_strnzcpylwr         -  Performed       27 tests 0.00 seconds used
  test 8 test_strnzcpyn           -  Performed       27 tests 0.00 seconds used
  test 9 test_strnzcpylwrn        -  Performed       27 tests 0.00 seconds used
  test 10 test_strnzcat           -  Performed   523264 tests 0.22 seconds used
  test 11 test_strnzcatn          -  Performed     2745 tests 0.00 seconds used
  test 12 test_strtokm            -  Performed       48 tests 0.00 seconds used
  test 13 test_atou               -  Performed   200010 tests 0.02 seconds used
  test 14 test_jtr_itoa           -  Performed  8400420 tests 0.39 seconds used
  test 15 test_jtr_utoa           -  Performed  8400420 tests 0.51 seconds used
  test 16 test_jtr_lltoa          -  Performed  8400420 tests 0.38 seconds used
  test 17 test_jtr_ulltoa         -  Performed  8400420 tests 0.73 seconds used
  test 18 test_trim               -  Performed    22736 tests 0.00 seconds used

**** Performing unit tests for functions from [common.c] ****
  test 19 test_ishex              -  Performed   122790 tests 0.02 seconds used
  test 20 test_ishex_oddOK        -  Performed   122790 tests 0.02 seconds used
  test 21 test_ishexuc            -  Performed   122790 tests 0.02 seconds used
  test 22 test_ishexlc            -  Performed   122790 tests 0.02 seconds used
  test 23 test_ishexuc_oddOK      -  Performed   122790 tests 0.03 seconds used
  test 24 test_ishexlc_oddOK      -  Performed   122790 tests 0.03 seconds used
  test 25 test_ishexn             -  Performed   479980 tests 0.20 seconds used
  test 26 test_ishexucn           -  Performed   479980 tests 0.10 seconds used
  test 27 test_ishexlcn           -  Performed   479980 tests 0.10 seconds used
  test 28 test_hexlen             -  Performed   469728 tests 0.07 seconds used
  test 29 test_hexlenl            -  Performed   237888 tests 0.04 seconds used
  test 30 test_hexlenu            -  Performed   237888 tests 0.04 seconds used
  test 31 test_isdec              -  Performed  1131077 tests 0.05 seconds used
  test 32 test_isdec_negok        -  Performed  2179654 tests 0.10 seconds used
  test 33 test_isdecu             -  Performed  2245190 tests 0.12 seconds used

**** Performing unit tests for functions from [sha2.c] ****
  test 34 test_sha224             -  Performed      129 tests 0.05 seconds used
  test 35 test_sha256             -  Performed      780 tests 0.08 seconds used
  test 36 test_sha384             -  Performed      908 tests 0.16 seconds used
  test 37 test_sha512             -  Performed      908 tests 0.17 seconds used
Performed testing on 37 total functions.
Total time taken : 4.60
```

退出码 0（`return any_failure` → 无失败）。
