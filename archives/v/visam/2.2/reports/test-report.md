# visam 2.2 测试报告

> **证据范围说明**：本报告中引用的 `reports/*.log`（各步骤原始输出）是本地验证产物，
> **未随 PR 提交**（随 PR 提交的证据为：本报告、`conan-verify-report.md`、`pr-body.md`、
> `15-finish.log`、`09b-refresh-patch.log`）。日志文件均可在同一环境中按 `notes.md`
> 「编译步骤（真实命令）」与「上游测试」两节给出的命令原样复现，下文每条结论都标注了
> 对应的命令与关键输出。这样做的原因是 PR 变更规模需控制在 AI 代码评审可处理范围内。

## 1. 上游测试

### 1.1 注册情况（清点证据）

`tests/Makefile.am` 只声明

```make
noinst_PROGRAMS = mvtest detest00 detest01 jvntest mvtest2
```

**没有** `TESTS=`、也没有 `check_PROGRAMS`，因此 `make check` 只编译不执行。
实测 (`reports/03-make-check.log`)：三个子目录均为 `make[1]: Nothing to be done for 'check'.`
→ **上游注册用例数 = 0**。

上游真实测试入口 = 上述 5 个测试程序（需在工作目录放置 `tests/TESTDATA`）。

### 1.2 实测结果（逐项）

| # | 用例 | 命令 | 退出码 | 关键输出 | 日志 |
|---|---|---|---|---|---|
| 1 | detest00（建库/双索引/写/顺序读） | `tests/detest00 200` | 0 | Records created 200 / read 200 | `reports/04-detest00.log` |
| 2 | detest01（第二索引定位后顺序读） | `tests/detest01 detest00` | 0 | Records read: 39 | `reports/04-detest01.log` |
| 3 | mvtest 建库 | `tests/mvtest create` | 0 | — | `reports/04-mvtest-create.log` |
| 4 | mvtest（事务压测 isbegin/iscommit/isrollback） | `tests/mvtest 200` | 0 | OPS OVERALL 5135 / committed 2473 | `reports/04-mvtest.log` |
| 5 | mvtest2 建库 | `tests/mvtest2 create` | 0 | —（建库无 stdout） | —（无输出，故未留空日志；同批次运行记录见 `reports/12-conan-create.log`） |
| 6 | mvtest2（非事务压测） | `tests/mvtest2 200` | 0 | OPS OVERALL 5314 | `reports/04-mvtest2.log` |
| 7 | jvntest（多文件/多索引，读 TESTDATA） | `tests/jvntest 5` | 0 | — | `reports/04-jvntest.log` |

**合计：7 次调用 / 通过 7 / 失败 0 / 跳过 0（通过率 100%）**

修复前（保留证据）：
- `reports/04-upstream-detest00.log`：未签名/未加载共享库时的 `symbol not found`
- `reports/06-mvtest-core-attempt.log`：mvtest SIGSEGV（rc=139）
- `reports/07-dbg-*.log`、`reports/08-dbg-*.log`：插桩定位到崩溃在 `vtranshdr()` 的根因证据

## 2. 适配后新增的鸿蒙消费者用例（test_package）

`test_package/main.c`（仅使用公开头 `visam.h` 与公开 API），3 条断言：

| # | 断言 | 说明 |
|---|---|---|
| 1 | `deccvdbl`/`dectodbl` 往返精度 | 唯一需要 OHOS `ecvt(3)` 兼容垫片的调用链 |
| 2 | `iswrite` 写入全部记录（200 条） | ISAM 写路径 |
| 3 | `isread(ISFIRST/ISNEXT)` 顺序读回全部记录 | ISAM 读路径 |

实测（`reports/11-consumer-run.log` 与 `reports/12-conan-create.log`）：

```
VISAM consumer test (visam 2.2)
[INFO] decimal round-trip: 1234.5678 -> 1234.5678
[PASS] deccvdbl/dectodbl 往返精度（覆盖 ecvt 兼容垫片）
[INFO] ISAM: written=200 readback=200
[PASS] iswrite 写入全部记录
[PASS] isread(ISFIRST/ISNEXT) 顺序读回全部记录
RESULT: OK
```

**消费者用例：3/3 通过（100%）**，由 `conan create`（`reports/12-conan-create.log`）与
`conan-verify`（`reports/conan-verify-report.md`）两次独立执行确认。

## 3. 门禁结果

| 门禁 | 结果 | 证据 |
|---|---|---|
| G1 配方完整性 | PASS | `reports/conan-verify-report.md` |
| G2 conan create（干净构建） | PASS | 同上 |
| G3 系统同名库隔离 | PASS | 同上 |
| G4 产物完整性 | PASS | 同上 |
| L2/L4/L5 | 见 conan-verify 报告 | `reports/conan-verify-report.md` |
| W3 本地 CI 模拟（JC/KC/L0/L1） | PASS | `reports/w3-local-ci.log` |

编译告警：仅 2 条上游既有告警（`libvisam/vbkeysio.c:576` 的 `-Wconstant-conversion`），
本适配未新增告警（ecvt 相关告警已通过垫片头文件声明消除）。
