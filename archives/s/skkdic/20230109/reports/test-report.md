# skkdic 20230109 测试报告

> **项目**: skkdic（SKK 日语输入法标准词典）
> **版本**: 20230109
> **测试日期**: 2026-10-11（上游 ERT 真实执行整改轮；首轮 2026-10-10）
> **测试环境**: HarmonyOS aarch64（os=OHOS、os.version=6.0、arch=armv8、
> compiler=clang 15、libcxx=libc++，profile ohos-aarch64-wsl）
> **测试类型**: 上游测试（2 个 Emacs ERT 用例，**真实执行**） + 消费者测试（test_package）

---

## 一、测试摘要

| 指标 | 上游用例 | 消费者/执行器断言 |
|:----:|:--------:|:-----------------:|
| 总数 | 2 | 73 |
| 通过 (PASS) | 2 | 73 |
| 失败 (FAIL) | 0 | 0 |
| 跳过 (SKIP) | 0 | 0 |

**通过率**: 上游用例 100%（2/2）；断言 100%（73/73）

> 上游 `zipcode/test/zipcode-test.el` 的 2 个 Emacs ERT 用例
> （`jisyo-zipcode/test1`、`jisyo-office-zipcode/test1`）由 test_package 用制品仓
> 已发布的 `emacs/29.1` **真实执行**，命令逐字对齐上游
> `zipcode/Makefile.in:116-118` 的 `test` 目标，实测
> `Ran 2 tests, 2 results as expected, 0 unexpected`。

---

## 二、测试结论

### 2.1 总体评价

通过。词典被完整安装到 share/skk/，内容格式解析正常；上游自带的 2 个 ERT 用例
真实执行并全部通过；反向破坏测试证明断言（含上游用例）确实依赖被测包的真实产物。

### 2.2 主要问题

无。本包为纯数据包，无可执行产物，因此 CI 的 L2（--version/--help 冒烟）与
L4（readelf NX/PIE/RELRO）对它按设计跳过/告警，不构成缺陷。

### 2.3 可用功能清单

- 37 个 SKK 词典文件安装到 <package_folder>/share/skk/
- package_info() 通过 cpp_info 属性 skkdic_datadir 发布数据目录
- 核心词典内容可解析（SKK 行格式 reading<空格>候选1/候选2//注释/）
- 上游 zipcode 词典中的邮编条目可按上游自己的用例逐字节校验通过
- ChangeLog / README.md / unicode-license.txt 随包安装
- 无命令行工具（本包不提供可执行文件）

### 2.4 已知限制

1. 上游 Makefile 的词典**再生成**步骤（gawk/ruby/emacs + skk-dev/tools 工具链）
   未复刻：这些工具链在 CI clean 环境不存在，且分发 tarball 已包含全部生成结果。
   （注意：上游的 **测试** 步骤不属此列，它只需要 Emacs，已被真实执行。）
2. package_type 留空（OHOS 适配版 conan 不支持 data 枚举），因此包不声明
   commands.json——非 CLI 包本来也不需要。
3. 执行上游用例所需的外部框架（Emacs ERT）以 conan 包 `emacs/29.1` 形式引入，
   属 test_package 的测试期依赖；skkdic 自身仍为零依赖。

---

## 三、测试详情

### 3.1 源码完整性

| 项 | 值 |
|----|----|
| URL | https://deb.debian.org/debian/pool/main/s/skkdic/skkdic_20230109.orig.tar.gz |
| 期望 sha256 | dc4f1550b84c80882a0db0b7e6db47a1baed7b40a2f821d0355464ed36d2ced4 |
| 实测 sha256 | dc4f1550b84c80882a0db0b7e6db47a1baed7b40a2f821d0355464ed36d2ced4 |
| 期望大小 | 11454739 字节（skkdic_20230109-1.dsc 的 Checksums-Sha256） |
| 实测大小 | 11454739 字节（远端 content-length） |
| 结果 | PASS（逐字节一致） |

### 3.2 上游测试（2 个 Emacs ERT 用例，真实执行）

上游测试入口（逐字抄自 `zipcode/Makefile.in:116-118`）：

```make
.PHONY: test
test:
	$(EMACS) --batch --quick --directory test --load test/all-tests.el --funcall ert-run-tests-batch-and-exit
```

执行方式（`test_package/run_upstream_tests.sh`）：

| 项 | 值 |
|----|----|
| 测试来源 | 与配方同一个发布 tarball（sha256 固定），运行期现取现用、跑完即删，**仓库内不内置上游测试代码** |
| ERT 框架 | conan 包 `emacs/29.1`（OHOS aarch64 预编译包，制品仓 ohpcd），test_package 的测试期依赖 |
| 工作目录 | 已安装的 `<package_folder>/share/skk`（用例读 `./SKK-JISYO.*.zipcode`，被测数据就是包里那一份） |
| 用例文件 | `zipcode/test/zipcode-test.el`（`grep -c '(ert-deftest'` = 2） |
| 用例 1 | `jisyo-zipcode/test1` — SKK-JISYO.zipcode 邮编 `6020033` 的整条条目逐字节比对 |
| 用例 2 | `jisyo-office-zipcode/test1` — SKK-JISYO.office.zipcode 邮编 `1008926` 的整条条目逐字节比对 |

实测输出：

```
Running 2 tests (2026-10-11 16:45:41+0800, selector `t')
   passed  1/2  jisyo-office-zipcode/test1 (0.386959 sec)
   passed  2/2  jisyo-zipcode/test1 (0.799421 sec)

Ran 2 tests, 2 results as expected, 0 unexpected (2026-10-11 16:45:42+0800, 1.193107 sec)
```

执行器自检（14 项）随之全部通过：

```
UPSTREAM_CHECK_SUMMARY tests=2 passed=2 checks=14 fails=0
```

| # | 执行器自检项 | 结果 |
|---|--------------|------|
| 1 | emacs 可执行文件存在且可执行 | PASS |
| 2 | 已安装词典树存在 | PASS |
| 3 | SKK-JISYO.zipcode 已安装（用例 1 输入） | PASS |
| 4 | SKK-JISYO.office.zipcode 已安装（用例 2 输入） | PASS |
| 5 | 上游入口 all-tests.el 存在 | PASS |
| 6 | 上游用例文件 zipcode-test.el 存在 | PASS |
| 7 | EMACSLOADPATH 指向目录 | PASS |
| 8 | 用例文件里 `ert-deftest` 计数 == 2 | PASS |
| 9 | emacs ERT 退出码 == 0 | PASS |
| 10 | ERT 报告 `Ran 2 tests` | PASS |
| 11 | ERT 汇总 `0 unexpected` | PASS |
| 12 | 报告为 `passed` 的用例数 == 2 | PASS |
| 13 | 用例 `jisyo-zipcode/test1` 报 passed | PASS |
| 14 | 用例 `jisyo-office-zipcode/test1` 报 passed | PASS |

### 3.3 test_package/conanfile.py 断言（1 项）

| # | 断言 | 结果 |
|---|------|------|
| 1 | 配方发布了 skkdic_datadir cpp_info 属性（缺失即抛异常） | PASS |

### 3.4 test_package/test_skkdic.py 断言（58 项）

纯 Python 3 脚本，在 OHOS aarch64 guest 上运行，不产出任何构建产物。

| # | 断言 | 结果 |
|---|------|------|
| 1 | datadir 目录存在（os.path.isdir） | PASS |
| 2-41 | 20 个核心词典逐个 isfile + getsize > 0（各 2 项） | PASS |
| 42 | SKK-JISYO.L 有内容（lines > 0） | PASS |
| 43 | SKK-JISYO.L 有合法条目（entries > 0） | PASS |
| 44 | SKK-JISYO.L 畸形行占比 <= 5% | PASS |
| 45 | SKK-JISYO.L 合法条目数 > 1000（实测 175786） | PASS |
| 46 | SKK-JISYO.zipcode 有内容 | PASS |
| 47 | SKK-JISYO.zipcode 有合法条目 | PASS |
| 48 | SKK-JISYO.zipcode 畸形行占比 <= 5% | PASS |
| 49 | SKK-JISYO.zipcode 合法条目数 > 0（实测 120394） | PASS |
| 50 | SKK-JISYO.assoc 有内容 | PASS |
| 51 | SKK-JISYO.assoc 有合法条目 | PASS |
| 52 | SKK-JISYO.assoc 畸形行占比 <= 5% | PASS |
| 53 | SKK-JISYO.assoc 合法条目数 > 0（实测 5950） | PASS |
| 54 | 安装的 SKK-JISYO.* 数量 >= 30（实测 37） | PASS |
| 55 | ChangeLog 已安装（isfile） | PASS |
| 56 | ChangeLog 非空（getsize > 0） | PASS |
| 57 | unicode-license.txt 已安装（isfile） | PASS |
| 58 | unicode-license.txt 非空（getsize > 0） | PASS |

实测输出：

    [PASS] core files: 20 files (OK) (40 asserts)
    [PASS] SKK-JISYO.L: 175786 entries (OK) (4 asserts)
    [PASS] SKK-JISYO.zipcode: 120394 entries (OK) (4 asserts)
    [PASS] SKK-JISYO.assoc: 5950 entries (OK) (4 asserts)
    [PASS] dictionary files installed: 37 (OK) (1 assert)
    [PASS] ChangeLog (OK) (2 asserts)
    [PASS] unicode-license.txt (OK) (2 asserts)

    === skkdic consumer test PASSED -- 58 assertions ===

断言总计：1（conanfile 属性）+ 14（上游执行器自检）+ 58（消费者测试）= **73**，
全部通过；另加上游 2 个 ERT 用例 2/2 通过。

### 3.5 反向破坏测试（证明测试非空壳）

本包产物全在 share/ 下，没有 bin//lib//include/，CI 的 L1e 会打印
[skip] No standard artifact dirs found to sabotage。因此手工做等价实验。

**(a) 上游 ERT 执行器**

| 轮次 | 操作 | 执行器退出码 | 结果 |
|------|------|--------------|------|
| 基线 | 未改动 | 0 | `tests=2 passed=2 checks=14 fails=0` |
| 破坏 1 | 删掉已安装的 `SKK-JISYO.zipcode` | **1** | `FAIL: SKK-JISYO.zipcode missing from …`，夹具不全即拒跑 ERT |
| 破坏 2 | 把 `6020033 /` 条目的**一个字节**改成 `X` | **1** | `FAIL: ERT summary reports 1 unexpected results`、`FAIL: upstream case jisyo-zipcode/test1 did not report 'passed'`；`tests=2 passed=1` |
| 复原 | 回到已安装目录 | 0 | `tests=2 passed=2 checks=14 fails=0` |

破坏 2 是关键：只改一个字节就让对应用例失败、且只让它失败 —— 上游用例确实在
逐字节比对包里的词典。

**(b) 消费者侧 Python 测试**

| 轮次 | 操作 | `conan test` 退出码 | 结果 |
|------|------|--------------------|------|
| 基线 | 未改动 | 0 | PASSED -- 58 assertions |
| 破坏 | mv `<pkg>/share` `<pkg>/share.bak` | **1** | `AssertionError: datadir not found` 或 `MISSING: .../share/skk/SKK-JISYO.L` |
| 复原 | mv `<pkg>/share.bak` `<pkg>/share` | 0 | PASSED -- 58 assertions |

破坏后必须真失败、复原后必须真通过 -> test_package 实质依赖被测包产物，
不是空壳测试。

---

## 四、本地同源门禁结果

命令：

    CI_PACKAGES=archives/s/skkdic/20230109 \
    JUNK_PR_DIFF=/root/tmp/pr_skkdic.diff \
    CONAN_PROFILE=ohos-aarch64-wsl \
    zsh ci/conan/build_and_test.sh

| 检查 | 结果 | 说明 |
|------|------|------|
| G0 知识图完整性 | pass | 知识图未被本 PR 改动 |
| G0e 根目录白名单 | pass | |
| KC 知识库质量 | pass | 知识库未被本 PR 改动 |
| JC 垃圾文件 | pass | 本 PR 只新增/修改文本文件（.py/.sh/.yml/.md） |
| L0 质量门禁 | pass | L0j 首次发布无版本冲突；L0k 判定为 library 包不需 commands.json；L0m/L0n 目录与分支名合规 |
| L1 测试执行 | pass | L1a test_package 被 conan create 执行；L1b 有运行痕迹；上游 ERT 在 test_package 内实跑 |
| L1e 反向验证 | skip | 无 bin/lib/include 可破坏（已手工补做两组破坏实验，见 3.5） |
| L2 冒烟（--version/--help） | skip | 无 bin/ 目录 |
| L4 安全扫描 | pass | 无补丁需签名 |
| L5 基线产物 | warn | 无 bin//lib/ 产物（纯数据包，按设计） |

    L0_RESULT=pass: all checks passed
    L1_RESULT=pass: test_package executed
    L2_RESULT=skip: no bin/ dir
    L4_RESULT=pass: no patches
    L5_RESULT=warn: no artifacts found

    Build Summary
      Total:   1
      Success: 1
      Failed:  0
      Pass rate: 100.0% (1/1)
    GATE_EXIT_CODE=0

**编译结束**: 2026-10-11（上游 ERT 真实执行整改轮）
**最终状态**: built
