# SKILL 执行流程反馈报告

> 本报告由 SKILL 自动生成，记录本次编译适配全流程中的失败、效率和改进发现。
> 文件位置: `feedback/SKILL_FEEDBACK_c94780b6.md`

---

## 背景

- **软件名称**: riscemu
- **版本**: 2.2.7
- **构建日期**: 2026-09-29
- **构建系统**: custom（纯 Python / poetry-core；`pip install --prefix --ignore-installed` 安装，无 C/C++ 编译单元）
- **上游仓库**: https://github.com/AntonLydike/riscemu
- **适配路径**: 路径 A（基础适配，无补丁）
- **补丁数量**: 0
- **编译依赖**:
无（运行时依赖 `pyelftools ^0.30` / `importlib-resources ^6.1.0` 由 pip 解析后随包内置，未声明 conan `requires`）
- **最终状态**: 成功（本地闭环全绿；PR 由用户手动创建）

---

## 情况

### 执行概要

本次 SKILL 执行流程涵盖从源码准备到 PR 提交的完整链路。以下是关键节点的执行情况：

| 阶段 | 步骤 | 结果 | 说明 |
|------|------|------|------|
| init-build | 源码下载/解压 | 完成 | GitHub 官方 tag archive `v2.2.7`（sha256 `d9d4da9b…bd0c`）；`init-build` 曾把 `sphinx-docs/` 误当源码根，手工按 `--strip-components=1` 重建 `.orig`/`.work`（对应 `E466`） |
| build | 编译构建 | 成功 | 构建系统: custom（`packaging/` 为空属正常——本包无二进制打包产物，仅 Python 前缀） |
| conan-verify | 配方验证 | 通过 | G1/G2/G3/G4 PASS，L2/L4/L5 完成；`conan create` RC=0，配方 rev `a009a87241d285ee9d43f75e7d6232cb`（修复后） |
| finish | 归档收尾 | 完成 | W3 本地 CI 模拟通过（`JC/L0/L1/L4/L5` pass，`Pass rate 100.0%`）；`.ci-result.json` `exit_code=0` |
| submit | PR提交+AI检视+CI | 未执行（按任务约束） | 任务明确要求不调用 `submit` / `gitcode_pr.py create-pr`，PR 正文已产出（`PR正文/pr_riscemu_2.2.7.md`），由用户手动建 PR 并触发 `/ai review`、`/rebuild` |

### 失败与问题

本次流程未遇到阻塞性问题。以下为需要人工介入/工具修正的过程性问题（均已定位并绕过，不影响交付）：

1. **`junk_check` 退化为 full 模式导致误杀**：`origin/main`（`10395da8d2`）领先工作树基点
   （`58f056cd95`）时，`git diff origin/main...HEAD` 为空 → `junk_check.sh` 从 `incremental`
   退化为 `full`（`git ls-files`，107014 个文件），命中**其它包的历史遗留被跟踪杂项**
   （`archives/c/cloog/0.21.1/.build-closed`、`.staging-verified` 等 5 个），JC5 报
   `junk_check failed` 并阻塞 W3。**处置**：先 `git add` 本包改动并提交，使三点 diff 恢复为本包
   48 文件 → `检查模式: incremental` → `JC_RESULT=pass`。
2. **`finish` Step 3「G0 干净构建验证」对纯 Python 包不适用**：G0 走 autotools 流程直接
   `./configure`（本包无 `configure`，exit 127）。**处置**：按 `archives/g/gping/1.20.1-r0` 先例放置
   `.g0-manually-verified` 标记（JC5 白名单已覆盖），并在 `notes.md` 记录等价的干净构建验证
   （干净目录 + 空 venv + `pip install --no-cache-dir .` + `riscemu examples/hello-world.asm` + 上游 pytest）。
3. **`finish` Step 8 `gen_summary` 报错**：`'str' object has no attribute 'append'`（框架侧缺陷，
   不影响 W2/W3 结论）。
4. **`finish` Step 5b（W5）误报**：既有条目 `E219/E253/E305` 的 `root_cause`/`rec_approach`
   被判「为空」——实为 YAML 块标量 `|` 未被检查脚本识别（字段内容非空），属框架侧问题。
5. **上游 lit 套件在最小环境下假失败**：lit 16 的 `TestingConfig` 只转发 `PATH`，不转发
   `HOME`/`PYTHONPATH`，导致 `fibs.asm` 抛 `FileNotFoundError`（干净上游树复现 10 passed / 1 failed）、
   `snitch/*.asm` 找不到模块、`p2align.asm` 找不到 `riscemu` 脚本。**处置**：新增平台 shim
   `test_package/filecheck/lit.local.cfg`（转发 `HOME`/`PYTHONPATH`/`PATH`），不改上游任何测试文件，→ 11/11。
6. **工具探测被同名目录遮蔽**：`test_package/filecheck/` 使 `import filecheck` 命中 PEP 420
   隐式命名空间包，误判「已安装」→ `lit` 二进制缺失（`command not found`，127）。
   **处置**：改用 `shutil.which()` 探针 + 安装后复检。
7. **PyPI sdist 不含测试**：`riscemu-2.2.7.tar.gz`（sha256 `9f206b19…c499`）无 `test/`、无 `examples/`，
   无法满足 R51；改用 GitHub 官方 tag archive（含 `test/` 与 `examples/`）。
8. **上游 `riscemu.priv` 子系统不可导入**（`__init__` 未导出 `RunConfig` + 内部绝对导入 `from core.*`）：
   2.2.7 与 master 同缺陷；**保持忠实最小适配不打补丁**，在 `manifest.yaml`/`notes.md`/`test-report.md`
   显式声明该子系统未覆盖（`E431`）。
9. **远端 CI 首轮失败：测试子进程继承「不 EOF 的 stdin」导致交互式调试器挂起**（PR #13868 /
   worker PR-check #64986，`conan-build-test` ❌、其余步骤 ✅）。失败输出为
   `[FAIL] unexpected_exception:TimeoutExpired: ... -m riscemu -v .../fibs.asm -o libc timed out after 300 seconds`
   （`HMBS_TEST_PACKAGE_RESULT` 43 discovered / 42 passed，共耗时 333.7 s）。根因：上游 `fibs.asm`
   以 `ebreak` 结尾，riscemu 会进入交互式调试器（`code.InteractiveConsole.interact()`）**读 stdin**；
   本地 stdin 已 EOF 故立即返回，worker 的 stdin 是「已打开但不送数据也不 EOF」的管道，
   `subprocess.run` 继承后便阻塞到自身超时（CI 侧描述为「构建超时/交互式测试卡住」）。
   **处置**（不改任何上游测试文件）：①消费者用例 `run()` 统一 `stdin=subprocess.DEVNULL`
   （等价 lit 自有关闭子进程 stdin 的语义），单次超时 300 s → 120 s；②测试工具（pytest/lit/psutil/
   filecheck）改为装入 `tempfile.mkdtemp()` 临时 **prefix**，不再假定 worker 解释器目录可写；
   ③`psutil` 固定 `5.9.5`（本平台唯一有 `ohos_aarch64` abi3 wheel 的版本）并在不可得时自动去掉
   `lit --timeout`、以 `timeout_guard` 字段如实记录。**验证**：干净 venv + 受限 `PATH` 的真实
   `conan create` 触发全部回退分支后 RC=0（52/52 + 49 + 11），另以 `< <(sleep 60)` 复现首轮挂起场景，
   修复后 52/52 在 1.5 s 内完成。

### 知识图谱使用情况

- **引用知识条目**: `E466`（嵌套源码目录误判，`init-build` 阶段实际命中）、`E017`（源码下载镜像注入）、
  `E512`（依赖闭包假绿 → `pip --prefix` 需 `--ignore-installed`）
- **新增知识草稿**: 4 条 —— `E429`（lit 最小环境不转发 `HOME`/`PYTHONPATH`）、
  `E430`（`import` 探针被同名目录遮蔽）、`E431`（上游 `priv` 子系统不可导入）、
  `E432`（单数 `test/` 目录 + pytest/lit 双套件 + sdist 无测试需用 tag archive）
- **引擎命中情况**: 草稿目录 2565 条；`recipe-search` 可检索本配方（`finish` Step 2 已并入语料）
- **测试统计**: 总计 112, 通过 112, 失败 0, 跳过 0
- **未覆盖的错误模式**: 除上述 9 类外无新增未记录模式；1/2/5/6 类问题已分别沉淀或命中既有条目，
  第 9 类（stdin 继承导致挂起）已在「知识图谱覆盖」中建议新增为通用条目

### AI 检视结果

- **检视阶段到达**: 未到达（PR 未创建；按任务约束由用户手动提交后评论 `/ai review`）
- **变更摘要评估**: 49 个文件、3620 行新增，全部位于 `archives/r/riscemu/2.2.7/`（40）与
  `knowledge/drafts/`（8），无框架文件改动（W2 原子性检查：仅含配方变更）
- **检视意见数量**: —（待用户创建 PR 后由 `/ai review` 产生）
- **检视意见处理**: —

### CI 结果

- **本地 CI 模拟 (W3)**: 通过（两次修复后最终运行）—— `setup.sh` RC=0、`build_and_test.sh riscemu/2.2.7` RC=0；
  `检查模式: incremental (49 个文件)`、`JC_RESULT=pass`、`L0_RESULT=pass`、`L1_RESULT=pass`、
  `L4_RESULT=pass`、`L5_RESULT=pass`、`L2_RESULT=skip`（上游 CLI 无 `--version` 烟测入口）、
  `Success: 1 / Pass rate: 100.0%`；`.ci-result.json` `exit_code=0`、
  `log_sha256=bb8bdca2d38e741a73a0e42fd7cedb32e06229ef92d359aef84c7f0c798fcf07`
- **远程 CI (PR 校验)**: 首轮失败（`conan-build-test` ❌，PR #13868 / worker #64986）→ 已定位并修复（见「失败与问题」9）；
  修复后本地等价路径（含全部回退分支）均通过，待用户手动评论 `/rebuild` 重跑远端 CI
- **CI 失败原因**: 测试子进程继承 worker 上不 EOF 的 stdin，导致上游 `fibs.asm` 的 `ebreak` 进入交互式调试器后挂起超时
  （历史遗留被跟踪杂项导致的 JC 误杀已通过「先提交再跑」解决，见「失败与问题」1）

### 效率分析

- **HANDOFF 次数**: 2（G0 `clean-verify` 的预期性 HANDOFF 1 次；W3 首次失败 HANDOFF 1 次）；
  另有一次 CI 反馈驱动的修复轮（非 HANDOFF，由用户转达远端 CI 失败）
- **重试次数**: 2（①W3 因三点 diff 为空退化为 full 模式而失败 → 提交本包改动后重跑通过；
  ②远端 CI 首轮超时 → 修复 stdin/工具装配后本地等价重跑通过）
- **关键瓶颈**: ①`junk_check` 的 incremental/full 模式退化（影响面大、报错指向他包，定位耗时）；
  ②lit 最小环境缺 `HOME`/`PYTHONPATH` 导致的假失败排查；③纯 Python 包在 autotools 导向的
  G0/W3 门禁中的「语义不适用」需要人工判读；④CI 挂起的根因（stdin 语义）不在任何日志中显式呈现，
  需按「本地正常→CI 超时」的差异反推
- **耗时较长的步骤**: lit/filecheck 套件（`--timeout=5`，11 用例约 2–6 s，含 `psutil` 依赖）；
  `conan create`（G2 + W3 各一次全量构建）

<!-- EVENTS:BEGIN -->
### 过程事件时间线（自动记录，v12.10）

共 2 个事件（含 0 次 HANDOFF、0 次推进/恢复），由 harness 各闸门自动累积：

| 时间 | 事件 | 详情 |
|------|------|------|
| 2026-09-29T21:21:37 | skeleton_created | result_partial |
| 2026-09-29T21:21:37 | lang_checked | detected=python 与任务 python 匹配 |
<!-- EVENTS:END -->
---

## 建议

### SKILL 设计改进

1. **`junk_check` 增加「非本包文件」豁免/归属判定**：当 `git diff origin/main...HEAD` 为空时，
   `full` 模式会把全仓历史遗留被跟踪杂项（如 `archives/*/*/.staging-verified`）算到当前任务头上，
   建议：①在 `full` 模式按下发任务的软件名过滤归属；②或在 `incremental` 为空时先提示
   「请先提交本包改动」，再决定是否退化。
2. **非 autotools 包的 G0 语义分流**：`clean_verify` 已在 `conanfile.py` 含 `replace_in_file` 时
   把 configure 失败判为预期；建议对 `build_system: custom`（纯 Python/pip）或
   `cargo`/`nodejs` 等明确无 `configure` 的配方直接跳过 G0 并给「不适用」结论，
   避免每次都要人工判读并放置 `.g0-manually-verified`。
3. **W3/L2 烟测入口需可配置**：`L2` 以 `--version`/`--help` 为烟测入口，对未实现 `--version` 的 CLI
   只能 `skip`；建议允许配方声明 smoke 命令（如 `runenv` 下跑一条最小 `--help`/示例命令）。
4. **`gen_summary` 与 W5 字段校验修复**：`Step 8` 报 `'str' object has no attribute 'append'`；
   W5 对 YAML 块标量 `|` 字段误判为空。二者均会污染 `finish` 的「失败步骤」统计，
   干扰对真实门禁结果的判读。
5. **R52/CI 规程补充「子进程 stdin 确定性」检查项**：`test_package` 与上游测试驱动中任何可能
   读取 stdin 的子进程（交互式 REPL/调试器/`read`/`pause`）都应显式 `stdin=subprocess.DEVNULL`。
   远端 CI 的 45 分钟硬超时下，「本地秒过、CI 超时」的第一嫌疑应列为「交互式等待」而非性能问题；
   建议在 W3 反馈模板的失败分类中单列「stdin 继承导致挂起（TimeoutExpired）」并提供排查命令
   （`< <(sleep 60)` 复现、`strace`/`--timeout` 对照）。

### 模板改进

1. **纯 Python（`python-require`）配方模板**：现有模板以 cmake/autotools/meson/makefile 为主，
   建议补充 pip 前缀安装模板，内置：`--prefix=<stage> --ignore-installed`、
   `runenv_info` 暴露 `PYTHONPATH`/`PATH`、不声明 `bindirs`、`package_info()` 自包含性判据。
2. **`test_package` 双判据模板**：建议在模板中固化「消费者断言的 site-packages 隔离运行」+
   「上游测试套件副本 + 平台环境 shim」两段式结构，并预置计数正则与 `HMBS_*` 标记写法，
   减少各任务重复实现（本包 52 条断言 + 上游 60 用例即按该结构落地）。
3. **PR body 模板补充「依赖闭包自包含性」小节占位**：纯 Python/解释型包的核心风险是
   「本地假绿」（宿主已装依赖），模板建议单列该证据项（本次已在「验证结果」中补充）。
4. **`test_package` 模板固化「确定性 stdin」与「临时 prefix 工具装配」**：①子进程调用统一带
   `stdin=subprocess.DEVNULL`（本次 CI 首轮失败根因）；②测试期工具装到 `tempfile.mkdtemp()` 的
   prefix 并把 `<prefix>/bin` 与 `site-packages` 注入子进程环境，不假定解释器目录可写；
   ③可选工具（如 `psutil`）缺失时降级而非中断，并在 `HMBS_*` 标记中记录实际生效的选项。

### 自动化补全

1. **`init-build` 源码根探测**：对含 `sphinx-docs/`/`docs/` 且根目录无构建脚本的仓库，
   建议以「是否存在包管理器清单（`pyproject.toml`/`setup.py`/`Cargo.toml`/`CMakeLists.txt`）」为
   第一判据，避免把文档目录提升为源码根（对应 `E466`）。
2. **工具链探针统一为 PATH 探针**：测试期工具（`lit`/`filecheck`/`pytest`）的「是否已安装」判断
   建议一律用 `shutil.which()`/`binary --version`，禁用 `import <tool>`（易被同名测试目录遮蔽，
   对应 `E430`）。
3. **解释型包的环境转发自动化**：对 lit/pytest 等「最小环境不转发 `HOME`/`PYTHONPATH`」的框架，
   建议在技能内提供标准 shim 片段（本次 `lit.local.cfg` 可复用），并自动写入 `notes.md` 问题表。
4. **`pip` 安装幂等复检**：安装后自动复检目标模块/脚本是否真实落盘（`pip --prefix` 遇
   「Requirement already satisfied」会静默跳过），并在日志中固化 `--ignore-installed` 提示。
5. **`pip --prefix` 的解析行为坑与回退链**：实测 `pip install --prefix <dir> psutil==5.9.5` 会
   选中 sdist 并在 `platform ohos is not supported` 处失败，而同版本 `ohos_aarch64` wheel 明明存在
   （`pip download --only-binary=:all:` 可取得）。建议工具安装固定为「常规 → `--only-binary=:all:`
   重试 → 可选工具降级」三步链，并把每步结果打进日志，避免把平台可解决的依赖误判为不可用。

### 知识图谱覆盖

1. **建议新增 E-entry：`junk_check` incremental→full 退化导致他包历史杂项误杀本包 W3**
   （症状 `JC_RESULT=fail: junk_check failed` + `检查模式: full (N 个文件)`；处置：先提交本包改动）。
2. **建议新增 E-entry：autotools 导向的 G0 对纯 Python/解释型包的「不适用」判定与
   `.g0-manually-verified` 先例**（含等价干净构建验证清单）。
3. **建议补强既有条目**：`E429`（lit 环境转发）、`E430`（PATH 探针）、`E432`（sdist 无测试 →
   tag archive；`snitch` 等测试辅助模块不随 wheel 发布需随副本提供）已在本次新增；
   建议后续把「上游子系统源码缺陷（绝对导入/导出缺失）→ 如实记录不打补丁」的处置口径
   归并进一条通用条目（本次为 `E431`，`riscemu.priv`）。
4. **建议新增 E-entry：可能读取 stdin 的交互式子进程在 CI 上永久挂起**（症状：本地秒过、CI
   `TimeoutExpired`（如 300 s）/构建超时；根因：`subprocess` 继承「打开但不送数据也不 EOF」的
   worker stdin，交互式调试器/REPL 等待输入；处置：`stdin=subprocess.DEVNULL`，等价 lit 关闭
   子进程 stdin 的语义）。这是跨语言、跨构建系统的通用模式，建议单独立条并关联 `E429`。
5. **建议新增 E-entry：`pip install --prefix` 优先选中 sdist 而弃用同版本平台 wheel**
   （症状：`platform ohos is not supported`；处置：`--only-binary=:all:` 重试，仍不可得则降级），
   与既有「`pip --prefix` + `--ignore-installed` 不自包含」（`E512`）属同一工具族的两个坑，建议互链。

---

## 作者

- **姓名**: li_shuo
- **邮箱**: ls.fr@qq.com
- **Agent ID**: 4EA2
- **生成时间**: 2026-09-29 21:21:37
- **PR 编号**: —
- **Git Commit**: 58f056cd95
