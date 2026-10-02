# DRAFT-lldb001-lldb-cli-ptrace-sandbox-rejection

> OHOS 设备沙箱在 syscall 级拒绝进程控制类调用：lldb inferior 启动 / gtest 进程控制用例 EPERM
> 来源：lldb/0.0.1 鸿蒙 PC 适配（2026-09-28 全量 + 09-30 自检修正）· 待主编 promote

## 现象

- lldb CLI 启动 inferior：`error: Cannot launch '<path>': ptrace failed: Permission denied`（45 例可见）
- launch 下游：`Command requires a process which is currently stopped` / `process must be launched` / `unable to evaluate...must be stopped`（5 例）
- 需目标进程但 FileCheck 窗口无 error 行的 shell 失败（36 例：15 探针实证 + 21 同族推定）
- gtest：Host 8（pipe bind EPERM）/ Target 13（spawn EPERM）/ DAP 4（mkfifo EPERM）/ lldb-server 3（ptrace EPERM）
- 正控：普通 exec 允许（`/bin/ls` 直接运行 rc=0）→ 被拒的是进程控制 syscall 族，不是"不能启动"

## 根因

OHOS 设备内核级沙箱策略在 syscall 层拒绝 ptrace / 匿名 FIFO / unix socket bind（三者直接探针均 EPERM）。
稳定策略非抖动：09-28/09-30 两日独立全量重跑 120 例失败测试集 byte-identical（签名逐例吻合）。

## 边界（重要）

本构建无 python（`SWIG_EXECUTABLE-NOTFOUND` + `LLDB_ENABLE_PYTHON=Auto`）→ API 套件 1342 例 0 执行。
**未观测到任何放行正控上下文**——「SB API 1342/1342 全过」为误读（unsupported ≠ 通过），
「沙箱按 tracer 进程上下文生效（python 路径放行）」推论已撤销。无正控不得下上下文级策略结论。

## 处理（rec_approach: attribute-to-env-with-evidence-grading）

1. syscall 级直接探针（`os.mkfifo` / `socket AF_UNIX bind` / `lldb -b -o run` 最小 inferior）——EPERM 坐实即环境因素
2. 复现矩阵（前台/后台 × 裸参数/lit 同参数）排除 harness 因素（本例 4/4 同错）
3. 报告证据分级：可见 error 行 / 探针重跑 / 同族推定——三级不可混写
4. EPERM 禁止按配方问题调参（R43）
5. PR 边界声明正面优先：「核心功能已全量验证 + 实际进程调试工作流受设备沙箱限制」（17.0.0 K4 同类同口径）

## forbid

- `conanfile.*ptrace|EPERM.*CMAKE|ptrace.*-D`：EPERM 为内核级策略，无配方侧解；按配方问题调参即 R43 调参螺旋

## 证据

- `archives/l/lldb/0.0.1/test-evidence/`：两日原始日志 + 逐例分类 + 15/15 探针 + 4/4 复现矩阵 + P1/P2/P3 正控探针 + 复现命令 + sha256
- 归因合计：120 = 86 launch 相关（65 直接 + 21 推定）+ 25 用例级 EPERM + 6 DWO + 1 CLI + 1 scripting + 1 Apple
