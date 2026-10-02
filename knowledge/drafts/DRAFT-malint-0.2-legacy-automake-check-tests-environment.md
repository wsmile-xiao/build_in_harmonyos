# DRAFT-malint-0.2-legacy-automake-check-tests-environment — 老式 automake 自定义 check 目标直接 exec 测试驱动脚本：`make check TESTS_ENVIRONMENT=sh` 命令行注入，零补丁

> 触发实例: malint 0.2 HarmonyOS PC shadow CI（2026-10-01）
> 库类型: autotools（autoconf 2.59 时代 Makefile.am，自定义 check 目标驱动 regress/runtest）

## 问题

malint 上游 `regress/Makefile.am` 是**并行测试框架（test-driver）出现之前**
的老式写法——自定义 `check:` 目标里直接执行测试驱动脚本：

```make
check: ../malint
	@failed=0; all=0; \
	for tst in ${TESTCASES}; do \
	  if ${TESTS_ENVIRONMENT} $(srcdir)/runtest $$t; then ...
```

HMDFS 上 `runtest` 无执行位（E046/E087），`make check` 全部 6 用例报：

```
zsh:5: permission denied: ./runtest
FAIL: frame-l3crc.test
...（6 of 6 tests failed）
```

## 根因

老式 Makefile.am 的 check 循环**直接 exec** `$(srcdir)/runtest`（不走
test-driver，LOG_COMPILER 无效），HMDFS 不授予脚本执行位（E046：chmod 不生效）。
但 Makefile.am 恰好预留了 `${TESTS_ENVIRONMENT}` 前缀变量——automake 官方
设计的测试环境注入点，可从 **make 命令行**覆盖，无需任何补丁。

## 方案

```sh
make check TESTS_ENVIRONMENT=sh
```

展开后每条测试命令变为 `sh $(srcdir)/runtest $$t`，runtest 由系统 sh
显式解释执行，绕开执行位要求。零补丁、零 Makefile.am 修改、不产生机械
diff，设备健康与否都适用（健康环境 `sh` 前缀同样正确）。

## 与既有条目/草稿的边界（查重说明）

- **kakasi 草稿**（HMDFS 无执行位 + sh 前缀）：针对 automake `check-TESTS`
  的 TESTS 脚本，且核心点是循环须容忍 `exit 77`（SKIP）——其方案是
  **放弃 make check 改配方内手写循环**；
- **libgctp 草稿**（`#!/bin/bash` shebang 全灭）：针对**并行 test-driver**
  框架，修法是给 Makefile.am 加 `LOG_COMPILER/TEST_LOG_COMPILER=/bin/sh`
  **补丁**；
- 本草稿：**老式自定义 check 目标**（前两者都不覆盖的第三种形态），
  修法是 `TESTS_ENVIRONMENT=sh` **make 命令行注入**——三种触发面
  （TESTS 脚本体 / 并行 test-driver / 自定义 check 循环）与三种修法
  （手写循环 / LOG_COMPILER 补丁 / 命令行 TESTS_ENVIRONMENT）一一对应，
  互不重复。

## 验证

- 真机：`make check TESTS_ENVIRONMENT=sh` → `All 6 tests passed`
  （frame-l3crc/frame-long/frame-short/id3v1-end/id3v1-noseek/id3v1-short
  6/6 PASS，run codex-0.2-malint-…-214011-40857，exit 0）；
- 空值注入（`TESTS_ENVIRONMENT=`）无效——make 命令行变量不能带尾随空格，
  必须恰好传 `sh`。

## 适用边界

- Makefile.am 自定义 check/test 目标中含 `${TESTS_ENVIRONMENT}` 占位
  （grep 确认）的老式 automake 项目；
- 优先级：能用命令行注入就不打 Makefile.am 补丁（无 diff、上游更新无冲突）。

## 反例与禁止

- 不适用并行 test-driver 框架（那是 LOG_COMPILER 的场景）；
- 不适用没有 TESTS_ENVIRONMENT 占位的自定义目标（此时才考虑 kakasi 式
  手写循环或 Makefile.am 补丁）；
- 不要用 `TESTS_ENVIRONMENT="sh "` 带尾随空格传参——make 会剥掉尾空格，
  得到空值注入，回到直接 exec 的失败。
