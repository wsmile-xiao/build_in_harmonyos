# W3（本地 CI 模拟）结果说明 — dinit-shutdown 0.21.0

- 被验证提交：`818f8c24fe40e09ee8724f0cbd43d725a9a6b5f0`
- 运行方式（与 `python3 scripts/ohc-run.py finish …` 的 Step5 阻塞门禁**同调用**；`scripts/ohc/workflow_checks.py:run_local_ci`
  在 finish 内发起的正是同样两条命令，仅日志前缀为 `$ setup.sh (RC=n)` / `$ build_and_test.sh … (RC=n)`）：

  ```console
  $ zsh ci/conan/setup.sh
  $ CI_PACKAGES=archives/d/dinit-shutdown/0.21.0 CI_REPO_ROOT=<worktree> zsh ci/conan/build_and_test.sh archives/d/dinit-shutdown/0.21.0
  ```

- 完整日志：`reports/w3-local-ci.log`（sha256 `cd2765fe259a18e7b3f3c5fbc45c5b3ff7c1b4c797bf8c36aba587493777b22c`，33557 字节）
- 结果：`Build Summary: Total 1 / Success 1 / Pass rate 100.0% (1/1)`

| 门禁 | W3 结果 | 说明 |
|------|---------|------|
| G0 | pass | 知识图谱完整性检查 |
| KC | pass | 知识完整性检查 |
| JC | pass | junk check（PR 改动清单按 pr.diff 基线） |
| L0 | pass: all checks passed | 质量门禁 L0a–L0o 全过（本轮 L0c 由 `test_package/test_dinit_shutdown.py` 满足） |
| L1 | pass: upstream tests + test_package executed | 上游 136 例 + test_package 阶段 |
| L2 | **skip** | 见下节：探针退出码口径缺陷，已人工补测（原始行见日志中 `L2_RESULT=skip:` —— 用 grep 定位，不写行号以免漂移） |
| L4 | pass: no patches | 本包无补丁（`patch_generation`/`patches/` 均不存在） |
| L5 | pass: bin/ has content | 产物基线详见 `reports/conan-verify-supplement.md` 的 L5 节 |

## L2 为何 skip，以及人工补测

W3 的 L2 smoke 探针（`ci/conan/build_and_test.sh`）只尝试 `--version` / `--help` 两个 GNU 长选项，
并要求退出码为 0。dinit 的 shutdown 工具按上游实现以**退出码 1** 打印 usage
（`src/shutdown.cc`：`if (show_help) { …cout << …; return 1; }`），于是 5 个产物全被判为 failed
并整组记为 skip：

```text
L2_RESULT=skip: dinit-halt version/help failed, dinit-poweroff failed, dinit-reboot failed, dinit-shutdown failed, dinit-soft-reboot failed
```

按流程第 7.2 节，此类 skip 必须人工补测，本包的人工补测记录在：

- `reports/conan-verify-supplement.md` 的「L2 消费者实测」节：5 个名字逐个实跑 `--help`，
  记录退出码 1、usage 首行回显自身 `argv[0]`、默认动作 `power down (default)`；以及 `-Z`
  未识别选项与无守护进程时的 `connect:` 失败路径；
- `reports/cli-behaviour.txt`：原始命令行为记录（含消费者测试程序的
  `RESULT: 39 checks, 39 passed, 0 failed`）。

**结论**：L2 的 skip 由探针退出码口径与上游 usage 语义不匹配导致，属工具判定缺陷，不是产物缺陷；
产物的真实命令行为已由上述人工记录与 `test_package` 覆盖。
