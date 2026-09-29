# squsq 3.3 — 测试报告（真机 conan create + 用例真跑）

> **原始日志说明（review-memory 规则 19）**：`*.log` 属仓库审查规则 19 定义的 **PR 禁止文件**，故本目录下的 `.log` 原件**不随 PR 提交**（保留在工作区本地）；本报告引用的日志名指本地原件，其**关键原始输出已内联于本报告**，结论可被独立复核。

日期：2026-09-24
环境：HarmonyOS PC aarch64（Conan 2.29.1 / OHOS SDK clang 15.0.4，`Target: aarch64-unknown-linux-ohos`）
profile：`ci/conan/profiles/ohos-aarch64`（host 与 build 同一份）
状态：**通过**（`conan create` 退出码 0；conan-verify G1–G4 + L2/L4/L5 全通过；
用例 **TOTAL 27 / PASSED 27 / FAILED 0 / SKIPPED 0**）

## 1. 复现命令

```bash
python3 scripts/ohc-run.py conan-verify squsq 3.3
# 内部执行：
conan create archives/s/squsq/3.3 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing --user=ohpcd --channel=stable
```

完整日志：`conan-create.log`（本地工作区原件，按规则 19 不随 PR 提交）（`conan-verify` 第二次运行时复用已装包，日志为 test_package 段全文，27 例结果在第 64–124 行）；门禁报告：[`conan-verify-report.md`](conan-verify-report.md)。

## 2. 构建过程（真实输出摘要）

```
squsq/3.3@ohpcd/stable: Calling source()   → t20-squsq-3.3.tar.gz (14654 B,
    sha256 aeafff976c18ffc178871be25b9bf403cb25414773ed4e8157813f98b8f3fb37)
squsq/3.3@ohpcd/stable: Calling build()    → "/data/service/hnp/bin/clang" -O2 -Wall \
        -Wno-error=return-type -Wno-error=int-conversion -o "<build>/sq"  sq.c tr1.c tr2.c sqio.c
                                            → "/data/service/hnp/bin/clang" … -o "<build>/usq" usq.c utr.c
squsq/3.3@ohpcd/stable: Calling package()  → bin/sq (27008 B), bin/usq (22912 B), share/doc/squsq/readme
======== Launching test_package ========
squsq/3.3@ohpcd/stable (test package): RUN: "python3" "…/test_package/test_squsq.py" "…/p/bin" --log "…"
TOTAL 27  PASSED 27  FAILED 0  SKIPPED 0
```

`dependencies: []` —— 全程无第三方包需要解析（上一阶段 W0 已实测本库第三方依赖为 0）。

## 3. 产物清单

| 路径 | 大小 | sha256 | 说明 |
| --- | --- | --- | --- |
| `bin/sq` | 27008 | `08ce15affb4cca3f5318402a3642510bc3255e0abd55cc8217e7e5a29d2caf5d` | `File squeezer version 3.3`，ELF64 AArch64，含 `.codesign` |
| `bin/usq` | 22912 | `a08fbc98bd198bbd2f1be2b16371e0fd5a525e8f4d057369ace5999f017dda70` | `File unsqueezer version 3.3`，ELF64 AArch64，含 `.codesign` |
| `share/doc/squsq/readme` | 2598 | — | 上游 readme（FreeBSD `PORTDOCS= readme` 对应） |

## 4. 用例结果

| 组 | 数量 | 通过 | 失败 | 跳过 | 日志 |
| --- | --- | --- | --- | --- | --- |
| 上游行为用例（readme / 源码 / 磁盘格式派生） | 24 | 24 | 0 | 0 | `upstream-cases-run.log`（本地工作区原件，按规则 19 不随 PR 提交）、`conan-create.log`（本地工作区原件，按规则 19 不随 PR 提交） |
| 鸿蒙特有用例（aarch64 / `.note.ohos.ident` / `.codesign`） | 3 | 3 | 0 | 0 | 同上 |
| **合计** | **27** | **27** | **0** | **0** | |

逐条用例名、来源、命令与断言见 [`upstream-test-cases.md`](upstream-test-cases.md)。
上游无自动化测试入口的证据见 [`upstream-test-entry.md`](upstream-test-entry.md)。

## 5. 门禁结果（conan-verify）

最后一次 `conan-verify` 报告见 [`conan-verify-report.md`](conan-verify-report.md)（`Verdict: PASS`）。
该次运行复用了已构建的包，故 L2/L4/L5 显示"跳过（无 cache 路径）"；三项已用独立命令复核，
证据见 `security-smoke-check.log`（本地工作区原件，按规则 19 不随 PR 提交）。

| 门禁 | 结果 | 说明 |
| --- | --- | --- |
| G0 预构建风险评估 | PASS | 构建系统未识别（上游无构建系统），跳过预查询 |
| G1 配方完整性 | PASS | conanfile.py + conandata.yml + test_package/（含 MANIFEST.yml）齐备 |
| G2 conan create | PASS | 干净源码构建 + test_package 27/27 |
| G3 系统同名库隔离 (R26) | PASS | 无 `lib/` 目录（纯可执行包），与 `/lib`、`/lib64` 无同名冲突 |
| G4 产物完整性 | PASS | bin/ 两个命令行工具 + share/doc 说明文件 |
| L2 smoke test | PASS | 独立复核：`sq --version`/`usq --version` exit=0；压缩→解压→逐字节比对一致 |
| L4 静态安全扫描 | PASS | 独立复核：`Type: DYN`（PIE）、`FLAGS_1: NOW PIE`、`FLAGS: BIND_NOW`、`GNU_RELRO R 0x1`、`GNU_STACK RW`（NX 生效） |
| L5 产物基线 | PASS | 产物 SHA256 基线记于下方"产物清单"与本报告 |

> `finish` Step 3 的 G0「干净构建验证」会按 autotools 假设运行 `./configure`，
> 本包上游并无 configure → `exit 127`（非阻塞项，已在 `notes.md` 记录）；
> 真正的干净构建验证由 W3（`ci/conan/build_and_test.sh` 内的 `conan create`）完成并通过。

## 6. 说明

* 上游 `make check` / `make test` 不可执行（无构建系统、无测试目标），已在
  `upstream-test-entry.md` 给出逐条证据；本包未修改、未跳过任何上游测试用例，因为上游用例集为空。
* `test_package` 27 例与第 ① 次「上游派生用例」为同一脚本的两次独立执行，
  分别作用于 conan 打包目录与 `conan create` 的 test_package 环境，结果一致。
* 第一次 `conan-verify` 曾失败于 `package()` 内 `self.run()` 返回值类型
  （Conan 2 返回 int，不能取 `.stdout`），修复见 `notes.md`。
