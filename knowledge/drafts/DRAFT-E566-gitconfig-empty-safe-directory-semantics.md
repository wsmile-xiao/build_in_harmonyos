# DRAFT E566 — gitconfig 内空值 `safe.directory` 的失效语义、误导性症状与静默写入来源

> 状态：待审草稿（UNMATCHED）｜发现时间：2026-09-10｜发现场景：tiny-aes 1.0.0 适配，阶段 A 建立 worktree 基线
> 关联条目：E101（同症状大类；**本条不否定 E101 的修复——实测其方案在本形态下依然有效**，定位是补强诊断与读取顺序语义）
> 定位：设备工作区层问题，与具体被测软件无关；影响本仓库全部多 worktree 适配任务

## 1. 现象：配置里明明有，git 仍说不安全

严格执行本仓库工作区规则（`GIT_CONFIG_GLOBAL="$MAIN_REPO/.gitconfig"`、`GIT_CONFIG_NOSYSTEM=1`）后，
worktree 内 git 命令失败：

```console
$ git -C "$MAIN_REPO" rev-parse HEAD
fatal: detected dubious ownership in repository at '/storage/Users/currentUser/ws/build_in_harmonyos'
To add an exception for this directory, call:
        git config --global --add safe.directory /storage/Users/currentUser/ws/build_in_harmonyos
```

而同一份配置文件里**已经**列出了该路径——症状自相矛盾，提示语只会让人"再 `--add` 一条"：

```console
$ git config --file "$GIT_CONFIG_GLOBAL" --get-all safe.directory | head -1
/storage/Users/currentUser/ws/build_in_harmonyos
```

## 2. 失效语义与最小复现

四份仅 2–3 行的配置，同一仓库，均以 `GIT_CONFIG_NOSYSTEM=1` 且**清除命令行层注入**后实测：

| 用例 | `[safe]` 段内容 | `git -C <repo> rev-parse --short HEAD` |
| --- | --- | --- |
| A | `directory = <repo>` | `7c11b6c082` ✅ |
| B | `directory = <repo>` 然后 `directory = `（空值在**段尾**） | `fatal: detected dubious ownership` ❌ |
| C | `directory = `（空值在**段首**）然后 `directory = <repo>` | `7c11b6c082` ✅ |
| D | 仅 `directory = `（空值，无有效条目） | `fatal: detected dubious ownership` ❌ |

**结论：空值条目使其之前读取到的条目失效；在其之后读取到、且匹配当前仓库的条目才能重建安全。**
B 失败是因为其后没有条目；C 成功是因为有效条目在空值之后。

**"匹配"是必要条件**（目标仓库固定为 `MAIN`，`OTHER` 为另一 worktree 路径）：

| 用例 | `[safe]` 段内容 | 结果 |
| --- | --- | --- |
| f1 | `OTHER`、空值、`OTHER`（两条均不匹配 `MAIN`） | ❌ 失败 |
| f2 | 空值、`OTHER`（不匹配 `MAIN`） | ❌ 失败 |
| f3 | `OTHER`、空值、`'*'`（`'*'` 匹配 `MAIN`） | ✅ `7c11b6c082` |

即"空值之后有任意条目"并不够，必须有一条**匹配该仓库**的条目。这也解释了污染现场为何整体失败：
空值（第 75 行）之后虽然还有条目（第 76 行的另一个 worktree 路径），但它不匹配当前操作的仓库。

> 复现时务必清除命令行层注入（`env -u GIT_CONFIG_COUNT -u GIT_CONFIG_KEY_0 -u GIT_CONFIG_VALUE_0 …`），
> 否则命令行层条目（优先级最高）会把三种形态全部"救活"，得出"该问题不存在"的错误结论——
> 本任务第一轮复现正是这样被自己的绕行配置污染的。

## 3. 读取顺序语义（决定"追加是否有用"）

配置读取顺序为 **system → global → local → 命令行层**。由于空值只重置"此前累积"的状态，
有效条目必须位于空值**之后**才能生效。实测：

| 组合 | 结果 |
| --- | --- |
| 污染文件为 global + 有效条目在 system（system **先**读） | ❌ 失败 |
| 污染文件为 system + 有效条目在 global（global **后**读） | ✅ `7c11b6c082` |
| 在 B 形态文件上执行 `git config --global --add safe.directory '*'`（追加落段尾 = 后读位置） | ✅ `7c11b6c082` |
| 同上但追加具体路径而非 `'*'` | ✅ `7c11b6c082` |

**因此 E101 的方案 A（`git config --add safe.directory`）在本形态下是有效的**：`--add` 总是追加到
段尾，即空值之后。本条目**不主张**"已知修复无效"，而是补上一条判据：当有效条目位于**先读**来源
（例如系统级 gitconfig）而空值位于**后读**来源时，追加到先读来源才会无效。

## 4. 根因与预防

- 空值条目来自固定动作 `git config --file <cfg> --add safe.directory "$VAR"` 在 `$VAR` 为空时的
  **静默写入**：git 不校验空值，命令返回成功，问题被推迟到下一次 git 操作才暴露。
  这与工作区规则已记录的"变量漏导出导致脚本静默回退"属同类形态（见 workflow 第 2 节）。
- 影响扩散：`GIT_CONFIG_GLOBAL` 指向该文件，故**所有 worktree、所有并发任务**同时失效。
- 预防：登记动作前加非空校验 `test -n "$VAR" && git config … --add safe.directory "$VAR"`；
  或任务开始时跑一次健康自检（见第 5 节）。

## 5. 处置

### 第 1 步：判定是否存在空值条目

```sh
git config --file "$GIT_CONFIG_GLOBAL" --get-all safe.directory | grep -n '^$'
```

命中即确认本模式（这是把"自相矛盾症状"快速归因的唯一必要步骤）。

### 第 2 步（出口 1，治本）：删除空值行，或按读取顺序追加到后读来源

- 删除空值行：幂等，不影响任何有效条目，不需要读写 token；
- 追加到后读来源：`git config --global --add safe.directory <path>`（会落段尾，实测有效）。

### 第 3 步（出口 2，不改共享配置、多任务并发安全）：命令行层注入

命令行层优先级高于所有文件层，且不写任何共享文件：

```sh
export GIT_CONFIG_COUNT=2
export GIT_CONFIG_KEY_0="safe.directory"; export GIT_CONFIG_VALUE_0="$MAIN_REPO"
export GIT_CONFIG_KEY_1="safe.directory"; export GIT_CONFIG_VALUE_1="$TARGET_REPO"
git -C "$MAIN_REPO" rev-parse --short HEAD   # 7c11b6c082 ✅
```

已验证生效，且不修改 `.gitconfig` 一字节。

## 6. 证据清单

| 项 | 路径／命令 |
| --- | --- |
| 污染现场 | `$MAIN_REPO/.gitconfig`，空值条目在**第 75 行**（前后均为有效条目）；该文件事后已被维护方清理，现值 76 行全为有效条目、`md5=056096a225cc6d4b99220a2d9d490378` |
| 冻结快照 | `$HOME/tmp/tiny-aes-1.0.0/bisect-76.gitconfig`（= 污染文件 head -76。注意：我的分割测试是按行截断，故 `head -75` 恰好切掉第 76 行那条"不匹配的后续条目"；空值行位于**第 75 行**）、`bisect-73.gitconfig`（head -73，无空值） |
| 匹配性对照 | `$HOME/tmp/tiny-aes-1.0.0/f{1,2,3}.gitconfig`（见第 2 节 f1/f2/f3） |
| 最小复现配置 | `$HOME/tmp/tiny-aes-1.0.0/repro-{A,B,C}.gitconfig`；本轮补充的 `c-{A,B,C}.gitconfig`（含 `*` 通配匹配用例 f3 与跨文件 d-*.gitconfig：`d-poison`/`d-other`/`d-emptyonly`） |
| 分半定位 | `head=73` 成功、`head=76` 失败 → 空值行位于两截断点之间（第 75 行；`head -75` 与 `head -76` 的差别还包括第 76 行那条不匹配条目） |
| 追加有效性 | `GIT_CONFIG_GLOBAL=<B 形态> git config --global --add safe.directory '*'` → 重测 `7c11b6c082` |
| 绕行验证 | `GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=safe.directory GIT_CONFIG_VALUE_0="$MAIN_REPO" git -C "$MAIN_REPO" rev-parse --short HEAD` → `7c11b6c082` |
| 反馈条目 | `$HOME/ws/feedback/pending/2026-09-10-tiny-aes-1.0.0.md`（高收益 第 2 条） |

## 7. 与 E101 的分工

| 维度 | E101 | 本条目 |
| --- | --- | --- |
| 触发根因 | HMDFS UID 映射使仓库 owner 与当前用户不一致 | 配置文件中存在空值 `safe.directory` 条目 |
| 症状 | `fatal: detected dubious ownership` | 同左，但**配置里已列出该路径**（自相矛盾） |
| 有效修复 | 增加一条生效的 `safe.directory`（方案 A/B/C） | **同样有效**；额外给出空值判定步骤与读取顺序判据，以及不改共享配置的命令行层注入 |
| 增量 | — | 空值的重置语义、读取顺序判据、静默写入根因与预防 |
