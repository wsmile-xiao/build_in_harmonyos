# 上游测试正式留档 — radamsa 0.7

- 被测构建：`radamsa/0.7@ohpcd/stable` 干净轮（conan create，2026-09-22，
  采信轮 HEAD `3c3e3538faa529abbaa71548f8f367ef743fb0fd`，分支 `feat/radamsa-0.7`；
  此后本分支仅 reports/** 文档级更新（T1），构建输入未变）
- 构建树：`~/.conan2/p/radam75473eb454fbc/s`（conan cache source folder，
  含 bin/ol、已补丁生成物 radamsa.c 与 bin/radamsa，即采信轮 G2 的同一构建树；
  两轮独立清缓存干净轮的安装产物 sha256 逐字节一致：bin/radamsa `ee70f744…8645b`）
- 沙箱 HOME：`$TASK_DIR/test-home`（任务私有目录，本机为
  `/storage/Users/currentUser/tmp/radamsa-0.7`；未触碰用户真实 HOME）
- 上游测试入口：`tests/run`（上游 Makefile `test:` 目标 → `.seal-of-quality`），
  遍历 `tests/*.sh`，每项最多重试 40 次（模糊测试断言是概率性的，重试是上游设计）
- 执行方式：与 `tests/run` 等价的逐项执行器（同一 40 次重试语义，另加单次尝试
  90 秒 python 子进程超时；toybox `timeout` 实测不杀子进程树不可用）。逐项命令形：
  `python3 - <run> tests/<name>.sh bin/radamsa`（/bin/sh 解释，cwd=构建树）。
  本留档对应第二轮采信轮的正式执行；第一轮独立干净轮的重放日志与本日志
  逐字节一致（diff 为空）。下方 fenced 块为执行器日志的逐字节留档：前几行是
  被测用例自身输出（tests/1k.sh 打印 "Generating 1k (trivial)"/"OK"），每用例
  以 `RESULT PASS|FAIL|TIMEOUT …` 结尾一行，末行 SUMMARY 为汇总。

抽取命令（两级自检通过：头部命令↔fenced 块一致、fenced 块↔磁盘原始日志逐字节
一致；fenced 块含末尾空行）：

```sh
# 本机复算（$TASK_DIR=/storage/Users/currentUser/tmp/radamsa-0.7，包目录见下）
sed -n '/^```text$/,/^```$/p' reports/upstream-tests.md | sed '1d;$d' \
  | diff - "$TASK_DIR/upstream-tests-formal.log" && echo IDENTICAL
```

计数口径：`TOTAL = PASS + FAIL + TIMEOUT(=SKIP/NOT_RUN) = 28 + 0 + 0 = 28`；
与声明 N=28（上游 runner `tests/*.sh` glob 注册数，框架注册数口径）一致；
N′ = 28。候选数法其余口径均 ≤28 并逐项归因：`*.sh_` 后缀停用 3 项
（blank.sh_ 空模板、tcp-client.sh_/tcp-serve.sh_ 网络守护形态）、
`tests/pcapng/` 2 项未接入 runner（glob 不下探子目录）、`tests/benchmark`
性能基准 1 项（非 .sh、非断言）。

```text
Generating 1k (trivial)
OK
RESULT PASS tests/1k.sh tries=1
RESULT PASS tests/ab.sh tries=1
RESULT PASS tests/bd.sh tries=1
RESULT PASS tests/fail.sh tries=1
RESULT PASS tests/ft.sh tries=1
RESULT PASS tests/ld.sh tries=1
RESULT PASS tests/li.sh tries=1
RESULT PASS tests/lr2.sh tries=1
RESULT PASS tests/ls.sh tries=1
RESULT PASS tests/meta.sh tries=1
RESULT PASS tests/nop.sh tries=1
RESULT PASS tests/num.sh tries=1
RESULT PASS tests/seek.sh tries=1
RESULT PASS tests/sha256-path.sh tries=1
RESULT PASS tests/sha256.sh tries=1
RESULT PASS tests/sr.sh tries=1
RESULT PASS tests/template.sh tries=1
RESULT PASS tests/tr.sh tries=1
RESULT PASS tests/tr2.sh tries=1
RESULT PASS tests/ts1.sh tries=1
RESULT PASS tests/ts2.sh tries=1
RESULT PASS tests/udp.sh tries=1
RESULT PASS tests/uniq.sh tries=1
RESULT PASS tests/xpd.sh tries=1
RESULT PASS tests/xpi.sh tries=1
RESULT PASS tests/xpn.sh tries=1
RESULT PASS tests/xpp.sh tries=1
RESULT PASS tests/xps.sh tries=1
RESULT SUMMARY pass=28 fail=0 timeout=0 total=28
```

结果：**28/28 全部通过**（上游用例零修改、零跳过、零失败；未打补丁的原版
二进制在本平台会在 1k.sh 等重定向 /dev/null 的用例上永久挂起，见
`reports/conan-verify-supplement.md` 的补丁对照）。
