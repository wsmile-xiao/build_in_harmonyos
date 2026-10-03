# DRAFT-pf9-commands-json-software-level-path-gate-contradiction

**闸门矛盾**：建 PR 前置闸 PF9 与 CI 的 L0k 对「CLI 工具的 `commands.json` 放哪」
给出互斥要求，**没有任何提交形态能同时满足**。

- 来源：sockstat 0.4.2 适配（2026-10-02）
- 严重度：🟡 medium（不阻塞代码，但会让每个 CLI 工具 PR 都被本地 preflight 拦）

## 矛盾在哪

| 闸门 | 要求 | 后果 |
|---|---|---|
| **CI L0k**<br>`ci/conan/build_and_test.sh` | `package_type=application` 或非空 `bindirs` 的包，**软件级目录**（版本目录上两级）必须有 `commands.json` | 缺失 → `L0k: CLI tool detected but commands.json missing (R38)`，`L0_FAILED=true` |
| **PF9**<br>`scripts/ohc/preflight.py` | `bad = [f for f in arch if len(f.split("/")) < 5]` —— 所有 `archives/` 变更路径必须 **≥5 段**（含版本目录层） | `archives/s/sockstat/commands.json`（4 段）→ `PF9 分支/路径闸: 变更路径缺版本目录层`，`create-pr` 拒绝 |

于是：**带 `commands.json` → PF9 拦；不带 → L0k 拦。**
而 `ARCHIVE-SPEC §6` 又明确要求软件级 `README.md` / `manifest.yaml` / `commands.json` 三件套。

已合入 main 的先例 —— `archives/t/tal/1.9` 与 `archives/n/net-tools/2.1` 带齐软件级
`README.md` + `manifest.yaml` + `commands.json`，`archives/d/dconf` 只带
`commands.json` —— 说明 **CI 侧接受**软件级文件，只是本地 preflight 过严。
这是闸门之间的矛盾，不是某个 PR 的问题。

## 处置

1. **先用证据坐实矛盾**，不要凭感觉跳闸：
   ```bash
   # a. CI 侧：L0k 对 application 包硬失败，commands.json 路径 = dirname(版本目录)
   # b. 本地侧：PF9 的 < 5 判定
   python3 scripts/ohc/preflight.py . origin/main HEAD
   # c. 本地同源门禁：带上软件级文件时是否全绿
   CI_PACKAGES="archives/s/sockstat/0.4.2" zsh ci/conan/build_and_test.sh
   ```
   三条同时成立才算坐实。
2. 走 SKILL 已定义的**逃生口** `OHC_PREFLIGHT=0` 或 `--no-preflight` 建 PR
   （与 `--no-ci-verify` 同一命名口径），并在 **PR 正文写明理由与证据行号** ——
   这是**登记例外**，不是静默跳过。
3. **不要**为了绕过 PF9 而把 `commands.json` 藏起来 / 改名 / 塞进版本目录：
   那会真的触发 L0k 红灯，且违反 R38 与 ARCHIVE-SPEC。
4. **根治方向**（提给主编 / 框架维护者，**不在本 PR 内改框架文件**）：
   PF9 应放行 `archives/<字母>/<包>/` 的直接子级软件级三件套
   （`README.md` / `manifest.yaml` / `commands.json`），只对版本目录之外的
   其他路径保持严格。

## 本条实证（sockstat 0.4.2）

- `python3 scripts/ohc/preflight.py . origin/main HEAD` → PF9 findings 恰为
  `archives/s/sockstat/README.md`、`commands.json`、`manifest.yaml` 三个 4 段文件
- `CI_PACKAGES=... zsh ci/conan/build_and_test.sh` → 8 阶段全绿
  （G0/KC/JC/L0/L1 pass，L2 skip，L4/L5 pass，构建 1/1）

两边同时成立 → 矛盾坐实 → 走逃生口 + PR 正文登记。

## 适用范围

- 任何 `package_type=application` 或产物含可执行文件的适配 PR（CLI 工具）
- 同时改动 `archives/<字母>/<包>/` 软件级文件与版本目录的 PR
- 需要用 `--no-preflight` 逃生口并登记理由的建 PR 场景
