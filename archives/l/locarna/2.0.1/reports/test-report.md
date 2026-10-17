# test-report.md — locarna/2.0.1（OHOS PC aarch64）

- 日期: 2026-10-09
- 环境: OpenHarmony PC, aarch64, clang/clang++ 15.0.4, autotools（上游预生成 configure/Makefile.in）, Conan 2.29.1
- Profile: ci/conan/profiles/ohos-aarch64（os=OHOS, arch=armv8, compiler=clang, libc++, cppstd=17, Release）
- 依赖: viennarna/2.7.2（+ 传递 check/0.15.2）

## 1. 上游单元测试（Layer 1：配方 build() 内 `make check`）

上游 automake 测试分两部分：Catch2 单元套件 `test_locarna_lib` 与集成驱动 `test_programs`（bash/perl，
需 /bin/bash 与 MLocarna Perl 模块，OHOS 不具备）。配方在 `make check` 命令行覆盖 `TESTS=test_locarna_lib`
只跑单元套件：

```bash
make -j1 check SHELL=/bin/sh TESTS=test_locarna_lib
```

结果: **22 test cases / 175 assertions, 0 failed**（exit 0）
配方据此产出证据标记：

```
HMBS_UPSTREAM_TEST_RESULT={"status":"passed","framework":"catch2",
 "command":"make check (test_locarna_lib)",
 "discovered":22,"executed":22,"passed":22,"failed":0,"skipped":0,"assertions":175}
```

## 2. test_package 消费者 + 端到端测试（Layer 2）

`test_package/test_liblocarna.cpp`：链接安装后的静态 `libLocARNA-2.0.a`（传递拉起 ViennaRNA），
构造 `LocARNA::Sequence s("test","ACGUACGU")`，断言
`s.seqentry(0).name()=="test"` 与 `s.seqentry(0).seq().str()=="ACGUACGU"` —— 验证头文件/链接接口
（含 include 双根 `include` + `include/LocARNA-2.0`）。

`test_package/conanfile.py` 的 `_cli_smoke()`（**鸿蒙特有测试**，针对本 PR 的 AArch64 修复回归）：

```bash
<package>/bin/locarna --version          # → LocARNA 2.0.1
<package>/bin/locarna seq1.fa seq2.fa    # → Score: 2928 + 两条 GGGGAAAACCCCUUUU 比对行
```

结果: **2/2 通过**（`--version` 输出与真实成对比对打分/序列断言）

```
HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":true,
 "command":"./test_liblocarna","discovered":2,"passedCount":2,"note":"ohos_runtime_cli"}
```

> 该测试是本 PR 核心修复（`patches/0001`）的回归：修复前 8 个 CLI 任意调用都会 100% CPU 空转、
> 零输出、`timeout` 返回 124，`--version` 本身即为一票否决式断言。

## 3. W3 本地 CI 模拟（finish step 5/10，阻塞门禁）

`ci/conan/setup.sh` + `ci/conan/build_and_test.sh locarna/2.0.1`，超时预算 3600s。

```
L0_RESULT=pass: all checks passed
L1_RESULT=pass: upstream tests + test_package executed
L2_RESULT=pass: exparna_p --version OK, locarna --version OK, locarna_deviation --version OK,
                locarna_p --version OK, locarna_rnafold_pp --version OK, locarnap_fit --version OK,
                ribosum2cc --version OK, sparse --version OK
L4_RESULT=pass: patches clean
L5_RESULT=pass: bin/ has content
Pass rate: 100.0% (1/1)
```

`reports/w3-local-ci.log`（gitignored）· `archives/l/locarna/2.0.1/.ci-result.json`（exit_code=0）

## 4. conan-verify 门禁

G0/G1/G2/G3/G4 全部 PASS，verdict=pass（`reports/conan-verify-report.md`）。
本地 G4 的包 ID 解析与 L2/L4/L5 因 `scripts/ohc/conan_verify.py` 的
`conan list <full-ref>:* --format=json` 结果键层级与代码假设不一致（`["Local Cache"][<full-ref>]`
vs 代码读取的 `["Local Cache"][<name>][<full-ref>]`）而跳过——属仓库级工具问题，不在本 PR 变更范围内；
等价的二进制冒烟由上表 W3 L2 对**全部 8 个二进制**逐一覆盖。

## 汇总

用例口径与 PR 正文（`reports/pr-body.md`）一致：**22 上游单元 + 0 上游集成 + 3 鸿蒙特有 = 25**。
W3 L2 的 8 次二进制冒烟属同一批断言之外的附加证据，单列不计入用例总数。

| 测试 | 数量 | 通过 | 失败 |
|------|------|------|------|
| test_locarna_lib（上游 Catch2 单元） | 22 用例 / 175 断言 | 22 / 175 | 0 |
| test_programs（上游集成驱动） | — | 不适用 | 平台不具备（无 /bin/bash + 无 MLocarna Perl 模块），配方内剔除并在 PR 披露 |
| test_liblocarna（消费者 API，鸿蒙特有） | 1 | 1 | 0 |
| locarna CLI 端到端（鸿蒙特有） | 2 | 2 | 0 |
| **鸿蒙特有小计** | **3** | **3** | **0** |
| **合计（用例口径）** | **25**（22 + 0 + 3） | **25** | **0** |
| W3 L2 二进制冒烟（附加证据，不计入用例总数） | 8 | 8 | 0 |
