# SKILL: 依赖二进制断链诊断（dep-binary-probe）

> 版本 1.0.0 · 适用 Conan 2.x + 鸿蒙 PC（OHOS aarch64）三方库适配流程
> 定位：把"依赖没发布"从**几十分钟后的深层编译错误**，提前成**一次廉价探测 + 一份可直接上报的证据**。

## 1. 一句话说明

Conan 制品仓里 **「配方存在」不等于「二进制存在」**。本 SKILL 做三件事：

1. 判定每个依赖「二进制可用 / 配方在仓但二进制缺失 / 配方都没有」；
2. 判定源码兜底「`--build=missing` 是否可行」（工具链是否也缺二进制）；
3. 输出机器可读结论 + 证据串 + 一条可直接执行的止损上报命令。

## 2. 适用范围

### 2.1 适用（任一满足即可用）

| 场景 | 具体表现 |
|------|---------|
| 适配前依赖预检（对应工作流 W0） | 在 `init-build` / 写 `conanfile.py` 之前，确认每个依赖真的能下载到二进制 |
| 疑似依赖引起深层编译失败 | `conan create` 的失败点落在**依赖**的构建里，而不是本包源码里 |
| “本地能过、CI 不能过” | 同一依赖本地有缓存二进制、CI 干净环境没有（结论漂移） |
| 兜底方案评估 | 想用 `--build=missing` 从源码兜底，但不确定工具链是否齐备 |
| 止损上报 | 需要 `result --status dependency_missing` 的 `--missing` 与 `--missing-evidence` |

### 2.2 不适用（不要用本 SKILL 判断）

| 情形 | 原因 / 应做什么 |
|------|----------------|
| 纯 header-only 且无 `tool_requires` | 没有依赖可探 |
| 同机同 `CONAN_HOME` 下 `conan create` 已经全绿 | 那是比本 SKILL 更强的证据（W3 已完成），无需重复探测 |
| 判断“依赖的版本约束是否兼容” | 那是 `conan graph info` 的职责；本 SKILL 只判“有没有二进制” |
| 依赖连配方都没有，需要先适配 | 本 SKILL 只负责识别并指向 R36 的“先适配发布依赖”流程，不代为适配 |
| 判断平台上某功能是否可用 | 那是预扫描 / 知识图谱（`prescan`、`engine`）的职责 |

## 3. 问题背景：现有规则为什么不足

| 已有规则 | 覆盖到 | 仍缺的部分 |
|---|---|---|
| R35（禁止用 `conan list` 判断 binary） | 规定了“不许用什么” | 没给“该用什么、结果怎么读”的机械手段 |
| R36（依赖必须先发布，再构建下游） | 规定了发布顺序 | 没给“怎么确认它确实没发布”的判定口径 |
| W3（本地编译验证） | 在**本包**编译阶段暴露问题 | 暴露太晚 —— 此时已烧掉大量预算 |

实际会踩的两个方向：

- **假 OK（本地缓存污染）**：本地 `CONAN_HOME` 恰好缓存着该依赖的二进制（以前装过），
  探测得到“可用”，而 CI 干净环境并没有 → 本地绿、CI 红。
  → 对策：**隔离 CONAN_HOME 探测**。
- **假缺失（检索通道限制）**：cnb.cool 制品仓对 binary 的检索索引不完整
  （返回 “No packages found”，或 `system acceleration policy not enabled`），
  容易被读成“依赖缺失”。
  → 对策：**只以 `conan install` 的解析结果判定**，并把通道故障单独归为
  `REMOTE_ERROR`，禁止当作依赖缺失上报。

代价最高的一种情形是“以为能兜底”：二进制缺失时改用 `--build=missing`，但兜底本身
要先从源码构建工具链（如 `cmake`），而该工具在制品仓同样没有可用二进制 —— 于是编译在
依赖链深处失败，几十分钟后才暴露真正原因。
→ 对策：**`--check-fallback` 在动手之前把这条路也探掉**。

## 4. 使用说明

### 4.1 最小用法

```bash
# ① 探测若干依赖（把 <SKILL_ROOT> 换成本仓库 scripts/ohc-run.py 所在 skill 的根目录）
python3 skills/dep-binary-probe/scripts/dep_binary_probe.py \
    --requires wayland/1.24.0 wayland-protocols/1.47 \
    --profile-host ci/conan/profiles/ohos-aarch64 \
    --profile-build ci/conan/profiles/ohos-aarch64 \
    --package wev --version 1.1.0

# ② 连带判断源码兜底是否可行（会多花几次探测）
python3 .../dep_binary_probe.py --requires wayland/1.24.0 --check-fallback --json

# ③ 直接从 conanfile.py 取依赖（启发式，见 §7 限制）
python3 .../dep_binary_probe.py --from-conanfile archives/w/wev/1.1.0/conanfile.py
```

### 4.2 输入定义

| 输入 | 形式 | 说明 |
|------|------|------|
| 依赖清单 | `--requires name/ver [name/ver …]` | 直接给出引用；`name` 支持 `cmake/[>=3.18]` 这类版本表达式（原样探测，成功代表该表达式可解析出**某个**有二进制的版本） |
| 或 conanfile | `--from-conanfile <path>` | 从 `self.requires("…")` / `self.tool_requires("…")` / `requires = "…"` 提取字面量（启发式，不求依赖图） |
| 平台配置 | `--profile-host` / `--profile-build` | 对应 `-pr:h` / `-pr:b`；**必须与真实构建一致**，否则探测的是别的配置 |
| 制品仓 | `--remote-name`（默认 `ohpcd`）、`--remote-url` | 给了 `--remote-url` 会写进隔离 home |
| 包身份 | `--package` / `--version` | 仅用于生成止损上报命令（可选） |
| 兜底评估 | `--check-fallback`、`--max-probes <N>` | 见 §4.4 |
| 隔离控制 | `--no-isolate`、`--source-conan-home <dir>` | 见 §8.1；`--no-isolate` 仅供调试 |

### 4.3 输出定义

**退出码契约**

| 退出码 | 含义 | 调用方应做什么 |
|--------|------|---------------|
| `0` | 全部 `BINARY_OK` | 继续适配 |
| `2` | 存在缺失 / 工具缺口（`BLOCKED`） | 先发布依赖（R36）；本包按 §4.5 止损上报 |
| `3` | 通道故障（`NEEDS_REVIEW`）或工具/环境错误（`ENV_ERROR`） | 通道故障按 R41 重试；环境错误修环境 |

**JSON 输出（`--json`，或 `--out <path>` 落盘）**

```jsonc
{
  "tool": "dep-binary-probe", "version": "1.0.0",
  "conan_home": "/…/conan-home-xxxx",          // 本次探测使用的隔离 home
  "remote": "ohpcd",
  "profile": {"host": "…", "build": "…"},
  "results": [                                  // 每个依赖一条
    {"ref": "wayland/1.24.0", "status": "RECIPE_ONLY",
     "package_id": "50c1715c9d6630244edc1e29caf86880dfcc7907",
     "evidence": "ERROR: Missing binary: wayland/1.24.0:50c1715c…",
     "detail": "…原始输出片段（非 OK 时保留，便于人工复核）…"}
  ],
  "summary": {                                  // 分组结论
    "verdict": "BLOCKED",
    "binary_missing": ["wayland/1.24.0"],       // 配方在仓、二进制缺失
    "recipe_missing": ["dssi/1.0.0"],           // 配方都没有
    "remote_errors": [], "unknown": [],
    "build_tool_gaps": ["cmake/4.4.3"],         // 兜底工具链缺二进制
    "env_error": "",
    "evidence": "conan install --requires=wayland/1.24.0 -> Missing binary: …"  // 可直接塞进 result 上报
  },
  "verdict": "BLOCKED",                         // OK | BLOCKED | NEEDS_REVIEW | ENV_ERROR
  "build_tool_gaps": ["cmake/4.4.3"],
  "evidence": "…",
  "suggested_result_command": "python3 …/ohc-run.py result wev 1.1.0 --status dependency_missing …",
  "notes": ["已从 /…/.conan2 复制 settings.yml/global.conf/remotes.json", "…"]
}
```

**状态语义 → 动作对照表（核心判据）**

| status | 含义 | 下一步动作 |
|--------|------|-----------|
| `BINARY_OK` | 制品仓有可用二进制 | 继续适配 |
| `RECIPE_ONLY` | **配方在仓、二进制缺失**（最隐蔽：检索界面显示“存在”） | 依赖需补发布（R36）；本包立即止损 |
| `RECIPE_MISSING` | 配方都没有 | 依赖尚未适配：先适配并发布依赖，再回来 |
| `REMOTE_ERROR` | 远端 / 通道故障 | 按 R41 重试（≥3 次、跨度 ≥30 分钟仍不可达才止损）；**不得**当依赖缺失 |
| `UNKNOWN` | 输出无法归类 | 人工读 `detail` 原文，并把新特征补回本 SKILL |
| `BUILD_TOOL_GAP` | 兜底工具链自身无二进制 | `--build=missing` 不可行：不要试源码兜底，立即止损 |
| `ENV_ERROR` | 工具/环境错误（conan 不可用、无可写临时目录等） | 修环境；结论无效，不要据此上报 |

### 4.4 `--check-fallback` 做什么

用 `conan graph info --requires=<ref> --build=missing --format=json` 求出**会走源码构建**
的节点，再逐个探测其中 `context=build`（构建工具）的引用：工具若同样没有二进制，
则源码兜底这条路也是断的。`--max-probes`（默认 6）限制额外探测次数。

### 4.5 与既有流程的衔接

```
W0 依赖预检  ──► 本 SKILL（--requires / --from-conanfile）
                        │
        ┌───────────────┼───────────────────────────────┐
        ▼               ▼                               ▼
  全部 BINARY_OK    RECIPE_ONLY / RECIPE_MISSING   REMOTE_ERROR
        │               │                               │
   继续 init-build   ①先发布依赖（R36，拓扑序）      按 R41 重试
   写 conanfile.py   ②本包止损（下方命令）          （≥3 次 / ≥30 min）
                            │
                            ▼
        python3 $SKILL_ROOT/scripts/ohc-run.py result <包> <版本> \
            --status dependency_missing \
            --missing "<裸包名,逗号分隔>" \
            --missing-evidence "<summary.evidence>"
```

判定口径（与 SKILL 的止损规则一致）：**“换一台网络正常的机器能否解决？”**
能 → `dependency_missing`；不能（工具链/平台缺失）→ `env_unsupported`。

### 4.6 复现示例（离线，不需要网络与真实 conan）

```bash
python3 skills/dep-binary-probe/tests/test_dep_binary_probe.py
python3 skills/dep-binary-probe/scripts/dep_binary_probe.py \
    --conan "python3 skills/dep-binary-probe/tests/fake_conan.py" \
    --requires goodlib/1.0.0 badlib/1.0.0 nosuchlib/1.0.0 --check-fallback --json
```

## 5. 真实案例（2026-09-24 在鸿蒙 PC 上实测，输出为原文摘录）

### 5.1 案例 A：配方在仓、二进制缺失（`RECIPE_ONLY`）

制品仓只发布了 Release 二进制；用 Debug 配置探测即可稳定得到"配方能解析、二进制没有"的真实场景：

```bash
$ python3 skills/dep-binary-probe/scripts/dep_binary_probe.py --requires expat/2.8.2 \
    --profile-host ~/profile-debug --profile-build ~/profile-debug \
    --package wev --version 1.1.0 --json
· 探测 expat/2.8.2 -> RECIPE_ONLY          # 退出码 2（BLOCKED）
evidence: conan install --requires=expat/2.8.2 -> Missing binary: expat/2.8.2:00ac0ff4648b418e79a125d41fd7fe336f9308d7
suggested: python3 $SKILL_ROOT/scripts/ohc-run.py result wev 1.1.0 --status dependency_missing \
             --missing "expat" --missing-evidence "conan install --requires=expat/2.8.2 -> Missing binary: …"
```

要点：`Missing binary:` 后面的 `<ref>` 才是**真正缺二进制的节点**，未必等于 `--requires` 给的引用
（本例探测 `wayland/1.24.0` 时缺的是其依赖 `expat` 的 Debug 二进制）。报 `--missing` 前先读这一行。

### 5.2 案例 B：配方都没有（`RECIPE_MISSING`）

```bash
$ python3 … --requires liblo/0.34 dssi/1.0.0
· 探测 liblo/0.34  -> RECIPE_MISSING
· 探测 dssi/1.0.0  -> RECIPE_MISSING
evidence: conan install --requires=liblo/0.34 -> Unable to find 'liblo/0.34' in remotes. Required by 'cli'
```

→ 依赖尚未适配：先按 R36 适配并发布 `liblo`/`dssi`，再回来构建下游。

### 5.3 案例 C：版本区间无候选（实测措辞与直觉不同）

```bash
$ python3 … --requires 'cmake/[>=3.18]'
· 探测 cmake/[>=3.18] -> RECIPE_MISSING
evidence: ERROR: Package 'cmake/[>=3.18]' not resolved: Version range '>=3.18' from requirement
          'cmake/[>=3.18]' required by 'None' could not be resolved. Required by 'cli'
```

→ 连工具配方都不存在，`--build=missing` 这条兜底路同样断（比在依赖链深处失败早了几十分钟）。

### 5.4 案例 D：全部可解析（`BINARY_OK`，退出码 0）

```bash
$ python3 … --requires wayland/1.24.0 wayland-protocols/1.47 scdoc/1.11.0 \
      libxkbcommon/1.13.1 ladspa-sdk/1.17 fftw/3.3.10
· 探测 wayland/1.24.0 -> BINARY_OK
…（6 个依赖全部 BINARY_OK，退出码 0）
```

独立复核（在**另一个**全新 CONAN_HOME 里下载探测到的同一个 package_id）：

```
wayland/1.24.0#780e006283b9f3693a2267b486182de1:33fbd5ba675733658aba670ef78f154c1cb6c736 - Download (ohpcd)
wayland/1.24.0: Retrieving package 33fbd5ba675733658aba670ef78f154c1cb6c736 from remote 'ohpcd'
wayland/1.24.0: Package installed 33fbd5ba675733658aba670ef78f154c1cb6c736
```

### 5.5 结论只对"探测当次"有效

同一批依赖在本仓库的历史记录里曾判为"二进制缺失"，本轮实测已可解析（`wayland` 链）。
制品仓的发布状态会随时间变化，**历史结论不能复用到新任务**：每次适配前重新跑一次探测
（W0 的第一件事），拿到的是当下的真实状态。

## 6. 维护指南：遇到 `UNKNOWN` 怎么办

`UNKNOWN` 不代表依赖有问题，只代表**当前日志措辞没被归类**。处理步骤：

1. 读 `detail` 里的原始片段，找特征行；
2. 把特征行加进 `_RECIPE_MISSING_RES`（缺配方）/ `_REMOTE_ERROR_RES`（通道故障）对应元组；
3. **在 `tests/test_dep_binary_probe.py` 里加一条"逐字照抄该措辞"的用例**锁住行为。

本轮两个归类就是这样做出来的：

- `ERROR: Package 'dssi/1.0.0' not resolved: Unable to find 'dssi/1.0.0' in remotes.` —
  与既有模式 `Unable to find package` 差一个词，原先落到 `UNKNOWN`；
- `Version range '>=3.18' … could not be resolved.` — 版本区间无候选，同样属配方缺失。

## 7. 已知限制

| 限制 | 影响 | 规避 |
|------|------|------|
| `--from-conanfile` 是**启发式字面量提取**，不求解依赖图 | 条件分支里的依赖会全被收集（宁多勿漏，可接受）；用变量拼出来的引用提取不到 | 重要 ref 用 `--requires` 显式给出；提取结果以 `results[].ref` 为准 |
| `Missing binary: <ref>:<pkgid>` 中的 `<ref>` 是真正缺失的节点 | 可能不是 `--requires` 给的那个引用（见 §5.1） | 报 `--missing` 前先读 evidence 里的节点名 |
| 版本表达式（`cmake/[>=3.18]`）只判"能否解析出某个版本" | 解析成功 ≠ 该版本满足你的其它约束 | 版本兼容性交给 `conan graph info` |
| 结论绑定 `--profile-host` / `--profile-build` | Debug 与 Release 的二进制不同，profile 给错结论就错 | profile 必须与真实构建一致（见 §5.1 的正反两面） |
| 只判"有没有二进制" | 不判 ABI 兼容、符号冲突、运行期加载、平台功能可用性 | 那些交给预扫描 / 知识图谱 / W3 编译验证 |
| 网络不稳时措辞可能漂移 | 极端情况下 `RECIPE_MISSING` 与通道故障混在一起 | 结论可疑时按 R41 重试一次再决定是否上报 |

## 8. 隔离机制与环境适配

### 8.1 为什么必须隔离 `CONAN_HOME`（默认开启）

本机 `CONAN_HOME` 里若缓存着该依赖的二进制（以前装过），探测会得到"可用"，而 CI 干净环境
并没有 —— 这正是"本地绿、CI 红"的来源。默认行为：

1. `mkdtemp()` 建一个独立 home；
2. 从真实 home 复制 `settings.yml` / `global.conf` / `remotes.json`；
3. 注册 `--remote-url` 指定的制品仓；
4. 所有 `conan` 调用都指向这个 home。

| 开关 | 作用 |
|------|------|
| （默认）隔离 | 结论代表"干净环境" |
| `--source-conan-home <dir>` | 指定要复制配置的真实 home（默认 `$CONAN_HOME` 或 `~/.conan2`） |
| `--no-isolate` | 直接用当前 home，**仅供调试**：本地缓存会造成假阳性 |

### 8.2 鸿蒙上的 `conan` 必须用绝对路径（实测坑）

本机 `conan` 位于 `/…/usr/local/bin/conan`，权限位为 `-rwxrwx---`：shell 里能直接跑，
但子进程用**裸名** `conan` 经 `PATH` 查找会失败（`OSError: [Errno 2] No such file or directory`）。
因此本工具把命令首段解析为绝对路径后再执行，并把"命令不可执行"（rc=127 / `OSError`）
归为 `ENV_ERROR`：**结论无效，不要据此上报依赖缺失**。

### 8.3 工作目录

工作目录优先 `$TMPDIR`；不可写时自动回退到 `~/tmp/dep-binary-probe`（鸿蒙上 `/tmp` 只读）。

## 9. 测试与覆盖（补全测试说明）

本 SKILL 没有"上游实现"可继承 —— 探测工具、依赖 stub、测试三者都是本轮新增，因此
**测试为 100% 新增，无上游用例被修改**。

```bash
$ python3 skills/dep-binary-probe/tests/test_dep_binary_probe.py
...
Ran 26 tests in 2.913s

OK
```

| 分组 | 用例数 | 覆盖内容 |
|------|--------|---------|
| `TestClassify` | 9 | `RECIPE_ONLY` / `RECIPE_MISSING`（含实测措辞、版本区间措辞）/ `REMOTE_ERROR`（含 cnb.cool 检索接口限制）/ `BINARY_OK` / `UNKNOWN` / `ENV_ERROR` / 判定优先级 |
| `TestHelpers` | 9 | 依赖字面量提取、`graph info` JSON 提取（含实测"日志花括号 + 裸 `{` 首行"错位场景）、conan 绝对路径解析、verdict 判定、证据串生成、临时目录回退 |
| `TestEndToEnd` | 8 | 退出码契约（0/2/3）、止损上报命令生成、`--check-fallback` 工具缺口、跨版本同 package_id、隔离 home 生效、人读输出 |

测试完全离线：`tests/fake_conan.py` 是可注入的 conan stub（7 种输出模式），
不依赖网络、不依赖真实 conan、不写仓库工作区。补充的"逐字照抄真实措辞"用例（§6）
是防回归的关键 —— 真实措辞一旦变化，测试会先红，而不是静默落到 `UNKNOWN`。
