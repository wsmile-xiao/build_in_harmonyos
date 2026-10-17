# mdm 0.1.3 测试报告（test_package 消费者测试）

**HEAD**: 被引执行日志产生于 `774740e4453489079646c163a4f5c6004df3c7dd`；
本报告文本随 W4 整改 r2 的提交 `c5fe567292ef4a91253dbbf6dd592e8fb6a7bfe4`
及其后继并入。两版之间**未重跑门禁**（原因与影响见文末「日志锚点」节）。
**执行方式**: conan create --build=missing + test_package/conanfile.py（conan test，含框架 L1e 破坏性负向测试**一轮**）
**执行时间**: 2026-09-26 09:09–09:10（设备 A 机；逐事件时刻与行号见文末
「日志锚点」节。该轮属 774740e4 版，本整改文本所属 HEAD 尚未重跑，见同节披露）
**执行归属**: 配方与 test_package 由 主理-61 起草并推送 `5c032f5b80`（07:25）；W4 审计
r1 整改（含 R38 commands.json 归位）与 W3 转绿由 主理-66 完成（`e6fa23e92a` 09:03 /
`774740e445` 09:12）；本报告所属的 W4 整改 r2 由 主理-66 窗执行棒 棒-66d 完成。
旧写法「07:1x（设备 A 机，主理-61）」与被引证据路径全在 `~/qzy/主理-66-mdm-0.1.3`
（主理-66 名下 worktree）这件事打架 ⇒ 按事实改述为上面的时序。

## 测试数字（五维账本）

| 维度 | 数量 |
|---|---|
| 上游测试总数（静态清点） | 0 |
| 总测试数 | 9 |
| 通过 PASS | 9 |
| 失败 FAIL | 0 |
| 跳过 SKIP | 0 |

- 账本不变式: DISCOVERED(9) = PASS(9) + FAIL(0) + SKIP(0)，由 test.sh 末尾自检行实测
- 上游清点: `upstream_tests_exist: false`（27 条目无测试目录/文件、Makefile 无 check 目标、
  24 处 assert 为源码内 libc 防御性断言），证据 `reports/upstream-test-scan.txt`
- 正式判决（逐字符原文，不省略字段）:
  `=== 汇总 discovered=9 pass=9 fail=0 skip=0 合计=9 ===`、
  `VERDICT: PASS`、
  `HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":true,"command":"/bin/sh test.sh","discovered":9,"passedCount":9,"skipped":0}`
  三行同串出自 `reports/w3-local-ci.log` 与 `reports/conan-create.log`（两份日志的
  机器可读结果行逐字符一致）；精确行号见文末「日志锚点」节（该节同时说明本整改
  未重跑门禁）。旧版本正文抄录该
  JSON 时丢了 `"command":"/bin/sh test.sh",` 字段，已按原文补回。
- L1e 破坏性负向测试只有一轮（旧版写「二轮」）：步骤行 `[step] L1e: Destructive
  negative test (R34)...`、唯一一条 `[sabotage] bin/ moved away`、唯一一条
  `[ok] L1e: Negative test confirmed — test genuinely depends on mdm` 各出现 1 次，
  且全在 `reports/w3-local-ci.log`；`reports/conan-create.log` 全篇无 L1e 段
  （复算: `grep -c "L1e\|sabotage" reports/conan-create.log` -> 0）。

## 结论

✅ 通过（9/9 实测通过、0 失败、0 跳过——全部断言真执行打包二进制）

## 测试面构成（9 条）

- A 产物面（5）: mdm-run/mdm-master/mdm-slave 存在且可执行、mdm-run ELF magic、
  mdm-top 裁剪校验（包内无 mdm-top，交付口径披露）
- B 功能面（4）: mdm-run 真实 exec（`/bin/sh -c "echo mdm-hello"` rc=0、stdout 透传校验）、
  无命令参数 rc=1 拒绝空跑、子进程退出码透传（`sh -c "exit 3"` → rc=3）

## 已知限制

- 交付口径无未决项：9 条断言全部真实执行通过；mdm-top（ncurses 监控器）按交付
  口径裁剪（notes.md 披露）。
- ⚠ 门禁时效: 上述读数是 `774740e445` 那一轮的实测，**本整改文本所属 HEAD 尚未
  重跑 conan-verify / finish**（设备 inode 准入闸不放行）⇒ 提审前必须在能过闸的
  时机重跑并回填文末「日志锚点」节，否则该节的 9/9 与本节数字都只对 774740e4 负责。
- 补丁 0001 修的是上游 `execvp(*argv, ++argv)` 的无序求值 UB（clang 15 实测报
  -Wunsequenced）：`*argv` 与 `++argv` 对同一对象无序读写，求值顺序不同则被 exec
  的程序名在「mdm-run 自身（argv[0]）」与「用户命令（argv[1]）」之间取值，而参数
  向量此时已推进为 argv[1..] ⇒ 名称与向量错位；补丁拆出 `char **args = argv + 1`
  后 `execvp(args[0], args)`，把「exec 用户命令、参数向量自该命令起」确定化（等价
  gcc 下的实际行为与作者意图）。B 组断言即在该修复后验证。该口径与
  conandata.yml / notes.md / 版本级 manifest.yaml / 补丁文件说明块一致；旧写法
  「clang 下直通模式 exec 错误程序」方向说反了（那一侧恰是作者意图），已纠正。

## 执行环境

- 设备: 鸿蒙 PC A 机（aarch64，HarmonyOS）；CONAN_HOME: `~/tmp/ch/home-mdm`
- 依赖: 无（纯 libc）
- 日志: `reports/w3-local-ci.log`（正式 W3）、`reports/conan-create.log`（G2 create）、
  `reports/upstream-test-scan.txt`（上游清点）

## 日志锚点（W4 整改 r2 回填）

本节每个行号都是对盘上文件 `sed -n '<n>p'` 的实测值，**绑定 HEAD
`774740e4453489079646c163a4f5c6004df3c7dd`（09:12 提交）的那一轮执行**：

| 时刻 | 出处 |
|---|---|
| conan-verify 报告 09:09:47 | `reports/conan-verify-report.md:6`（Verdict: PASS 于 :3，G1/G2/G3/G4 于 :12/:26/:30/:34） |
| G2 conan create 导出 09:09:30 | `reports/conan-create.log:10`（原文标 UTC 01:09:30） |
| W3 本地 CI 导出 09:10:11 | `reports/w3-local-ci.log:108`（原文标 UTC 01:10:11） |

| 证据 | 文件:行 | 原文 |
|---|---|---|
| 9 条断言逐条 | w3-local-ci.log:224-232 / conan-create.log:151-159 | 两条区间各 9 行，逐条同为下列 |
| 汇总行 | w3-local-ci.log:233 / conan-create.log:160 | `=== 汇总 discovered=9 pass=9 fail=0 skip=0 合计=9 ===` |
| 机器可读结果 | w3-local-ci.log:234 / conan-create.log:161 | `HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":true,"command":"/bin/sh test.sh","discovered":9,"passedCount":9,"skipped":0}` |
| 判决 | w3-local-ci.log:235 / conan-create.log:162 | `VERDICT: PASS` |
| L1e 步骤行 | w3-local-ci.log:247 | `[step] L1e: Destructive negative test (R34)...` |
| L1e 唯一破坏动作 | w3-local-ci.log:248 | `        [sabotage] bin/ moved away` |
| L1e 唯一负向确认 | w3-local-ci.log:249 | `[ok] L1e: Negative test confirmed — test genuinely depends on mdm` |
| L1e 在 G2 日志中 | conan-create.log 全篇 | 0 命中（`grep -c "L1e\|sabotage" reports/conan-create.log` -> 0） |
| 打包清单 | w3-local-ci.log:188 / conan-create.log:115 | `package(): Packaged 4 files: mdm-run, mdm-master, mdm-slave, LICENSE` |
| 补丁应用行 | w3-local-ci.log:172 / conan-create.log:99 | `Apply patch (bugfix): programs/mdm-run.c: …` |

9 条断言逐条原文（`w3-local-ci.log:224-232`，`conan-create.log:151-159` 同串）:

```
PASS: A mdm-run 存在且可执行
PASS: A mdm-master 存在且可执行
PASS: A mdm-slave 存在且可执行
PASS: A mdm-run 是 ELF 镜像
PASS: A mdm-top 已按交付口径裁剪（包内无 mdm-top）
PASS: B1 mdm-run 真实 exec 命令（/bin/sh -c）rc=0
PASS: B2 被执行命令的输出透传回 stdout（mdm-hello）
PASS: B3 无命令参数 → rc 非 0（拒绝静默空跑，实测 1）
PASS: B4 子进程退出码透传（exit 3 → mdm-run rc=3）
```

### ⚠ 本整改未重跑门禁（必读）

W4 整改 r2（提交 `c5fe567292ef4a91253dbbf6dd592e8fb6a7bfe4` 及其后继）**没有重跑
`conan-verify` 与 `finish`**：设备准入闸 `~/tmp/uc2/gate.sh` 拒绝放行——`stat -f` 实测
$HOME 卷 inode 只剩 80,882（总量 48,455,677，已用 99.83%），低于该闸的 500,000 下限；
`df -i $HOME` 在本机 HMDFS 上常态只吐表头（闸门取不到数便按 `inode余=?` 放行），而取到
数的那一次直接返回 `GATE_FAIL:inode 余量 80812 < 500000`。不放宽判据、不带病起构建，
已把设备 inode 治理上报（`~/tmp/ch` 下累积 116 个 conan home）。

⇒ 因此上表的 9/9 是 **774740e4 版的实测**，不是本整改文本所属 HEAD 的实测。
本轮配方侧只改了注释与说明文字：补丁 hunk 逐字节未变，patch 后的
`programs/mdm-run.c` sha256
`85166d09bfb177d91bac849702a35bbf30918148f414fafd9d6475491b0769aa` 与那一轮一致；
但 conandata.yml 的 `patch_description` 变了 ⇒ **recipe revision 会变**，下一轮
`conan-verify` + `finish` 必须重跑，并重跑后回填本节全部行号与时刻。

### 证据件的入库范围

`.gitignore:96` 是 `reports/`，故 `reports/conan-create.log`、
`reports/w3-local-ci.log`、`reports/conan-verify-report.md` **不随 PR 走**；PR 内的
证据件只有本文件与 `reports/upstream-test-scan.txt`（两者早先已被显式 tracked）。
⇒ 机器可读结果行与 9 条断言原文都已逐字符抄进本节，第三方可凭 PR 内文本自证；
行号锚指向 A 机 `~/qzy/主理-66-mdm-0.1.3` 的工作树。
