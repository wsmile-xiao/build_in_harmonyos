- **三方库名称**：reflex
- **上游版本**：20241231
- **上游仓库地址**：https://invisible-island.net/reflex/（Thomas Dickey 维护的 flex 2.5.4 分支；发布源 https://invisible-island.net/archives/reflex/reflex-20241231.tgz，sha256 06a8c57fb666d74c8450e6aa2e471835a0ca2995b3621fb64f9cc4ce9daad6b6）
- **适配路径**：路径 A（基础适配）+ 路径 B（知识库扩展）—— 含 2 个补丁（1 笔上游缺陷修复 + 1 笔 HMDFS 平台适配）
- **使用知识库**：openharmony-compile-agent（§0–§7 流程与 52 条铁律）；知识命中并复用：E077（OHOS 上 ELF 须带 `.codesign` 才能执行 → `build()` 内先签名 `flex` 才能跑 `make check`，`package()` 内再签 `bin/reflex`、`bin/reflex++`）、E490（autotools helper 脚本执行位/HMDFS 相关，本包不适用——发布包脚本执行位完好）、裸命令名解析坑（本机 `posix_spawn` 快路径不做 PATH 查找 → 消费者测试脚本不得用 `["sh", "-c", ...]` / `["clang", ...]`）、HMDFS 临时目录坑（`config.status` 自建临时目录后立刻写入必 EACCES → 见补充说明第 7 条）
- **本次沉淀的知识草稿（路径 B，6 条，均在 `knowledge/drafts/`）**：
  1. `reflex-20241231-skel-c-flex-skl-mtime-divergence.{kv,md}` — 发布包"预生成骨架 vs 骨架源"内容分叉却 mtime 同秒 → make 不重生成，补丁必须打在生效文件上并用 `os.utime` 钉住确定性（可复用于 flex/bison 系及任何 dist 同时含生成物+模板的包）
  2. `reflex-20241231-cxx-skeleton-guard-misplacement.{kv,md}` — 生成器"仅非 C++"骨架区块边界错位 → C++ 模式输出引用仅作为成员存在的名字（可复用于任何"一套骨架多语言输出"的代码生成器）
  3. `reflex-20241231-reflexpp-stdout-form-required.{kv,md}` — C++ 生成必须走 `-t` stdout 形式，`-o` 会丢掉写在输出文件打开之前的 include 序言行
  4. `reflex-20241231-bootstrap-check-build-host-equality.{kv,md}` — autotools 自举 `make check` 仅在 `--build`/`--host` canonical 相等（`@no_cross@` 非空）时才执行，交叉构建下静默假通过（可复用于所有自举/自检类 target）
  5. `reflex-20241231-bigcheck-bare-c-compression-option.{kv,md}` — 上游测试目标自身不可用时的归属判定与"显式枚举可用模式 + 记录排除"处理范式
  6. `reflex-20241231-hmdfs-tmpdir-config-status-eacces.{kv,md}` — **本地全绿 / CI 间歇失败**的一类 autotools 失败：`config.status` 写不进自己刚在 HMDFS 上建的临时目录（同一代码一次失败一次通过，属时序竞态）；修法是把 TMPDIR 钉到经"写探针"验证的可写根 + 在 configure 侧显式 `chmod 700` 临时目录（可复用于所有 autoconf 包在 HMDFS 卷上的 CI）

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 0 | 上游无单元测试框架（无 tests/ 目录、无 CTest/gtest 注册） |
| 集成测试 | 1 | 顶层 `Makefile.in` 的 `check` 目标：自举回归 —— 用刚构建出的生成器重新生成 `scan.l` → `scan.c`，与发布包预生成的 `initscan.c`（由 `.bootstrap` 复制为 `scan.c`）逐字节比对，1 条断言 |
| 其他测试 | 6 | 上游 `bigcheck` 把同一条断言在 7 种表压缩模式下各跑一遍；其中裸 `-C` 项在上游即失败（见下方「补充说明」第 4 条），实际可用 6 种（`-Ce/-Cm/-f/-Cfea/-CFer/-l`），本 PR 逐条执行 |
| **合计** | **1** | 本仓 R51 口径：注册用例数 = 断言数（1 条逐字节比对断言，实测执行 7 次：默认 + 6 种压缩模式） |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 0 | 不变 | 上游无单元测试 |
| 集成测试 | 1 | 不变 | 上游 `make check` 在适配机由 `conanfile.build()` 内驱动，实测 **1/1 通过**；6 种表压缩模式复扫亦全部通过 |
| 鸿蒙特有测试 | 7 | 新增 | `test_package/test_reflex.py` 对安装产物实测 **7/7 通过**，其中 2 条为完整消费者端到端链路（生成 → 编译 → 链接 → 运行 → 断言词法流） |
| **合计** | **8** | **+7** | 上游 1 + 鸿蒙特有 7，全部通过 |

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例
- [ ] **是**，存在对上游测试用例的修改

> 未触碰 `Makefile.in` 的 `check`/`bigcheck` 目标与任何测试逻辑。两个补丁都与上游测试用例无关：
> `patches/0001-skel.c.patch` 打在**生成器骨架数组** `skel.c` 上（修的是生成器自身对 C++ 模式
> 的输出缺陷），且不改变 C 路径输出，故 `make check` 的自举比对仍逐字节成立；
> `patches/0002-configure-hmdfs-tmpdir.patch` 只改 `configure` 里"创建临时目录"的基础设施
> 三行（见补充说明第 7 条），不涉及任何测试逻辑。

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [ ] **否**，上游已有测试用例覆盖
- [x] **是**，上游无独立测试框架，适配后补全了测试

> - **补全的测试范围**：为交付包新增 7 个鸿蒙消费者用例（`test_package/test_reflex.py`），
>   覆盖安装产物的真实可用性而非存在性：T1 `reflex --version` 同时含谱系版本 `2.5.4` 与
>   补丁级 `20241231`；T2 `reflex++ --version`（安装期创建的同名符号链接是否随包发布）；
>   T3 `include/reFlexLexer.h` 同时声明 `FlexLexer` 基类与 `yyFlexLexer`；
>   T4 `lib/librefl.a` 为合法 ar 归档且导出 `yywrap`（用 `llvm-nm` 实证）；
>   T5 `share/man/man1/reflex.1` 已安装且非空；
>   T6 **C 端到端**：`reflex -o consumer.c consumer_c.l` → `clang -I inc src -L lib -lrefl`
>   （`librefl.a` 提供 `main()`/`yywrap()`）→ 运行 → 断言词法流 `NUM:42,ID:alpha,NUM:7,ID:_b9`；
>   T7 **C++ 端到端**：`reflex++ -t consumer.l > consumer.cc`（断言首行为
>   `#include <reFlexLexer.h>`）→ `clang++ -std=c++17 … -lrefl` → 运行 → 断言同一词法流。
> - **补全原因**：上游只有一条自举断言（证明「生成器能稳定复现自己的扫描器」），**不覆盖**
>   消费者视角的可用性——尤其不覆盖 C++ 路径，而本包恰好在 C++ 路径上存在上游缺陷（见
>   补充说明第 2 条）。`<tool> --version` 类通用冒烟门禁不足以判定「生成的扫描器能否编译运行」，
>   故必须补端到端用例。
> - **新增测试文件清单**：
>   1. `archives/r/reflex/20241231/test_package/test_reflex.py` — 7 条消费者断言
>      （每条例印一行 `SMOKE-PASS <name>`，失败打印 `SMOKE-FAIL <name>: <reason>` 并整体非零退出）
>   2. `archives/r/reflex/20241231/test_package/conanfile.py` — 先以 `self.run(...)`
>      真跑一遍（满足 CI L0d 的文本门禁），再捕获同一运行统计 `SMOKE-PASS` 行数，
>      输出 `HMBS_TEST_PACKAGE_RESULT={...}` 标记，`passedCount` 与 7 不符即抛 `ConanException`
>   3. `archives/r/reflex/20241231/test_package/MANIFEST.yml` — 上游测试声明与审计口径

## 验证结果

- 编译状态：**通过**（clang 15 / OHOS SDK 26.0.0.18，`--build=aarch64-linux-ohos
  --host=aarch64-linux-ohos`，`--disable-shared --enable-static`；`conan create` 全绿，
  状态 built）
- 上游测试用例通过率：**1/1（100%）**（适配机实测：`make check` 自举比对通过；
  另 6 种表压缩模式复扫全部通过）
- 新增测试用例通过率：**7/7（100%）**（`conan create` 内 `test()` 实测，
  证据行 `SMOKE-SUMMARY 7/7 checks passed`）

### 产物验证

| 项 | 结果 | 说明 |
|----|------|------|
| 编译无错误 | PASS | `conan create` 成功，`make check` 与 6 种压缩模式复扫全部 rc=0 |
| 产物存在性 | PASS | `bin/reflex`、`bin/reflex++`、`lib/librefl.a`、`include/reFlexLexer.h`、`share/man/man1/reflex.1` |
| ELF 可执行性 | PASS | OHOS 上 ELF 须带 `.codesign` 才能执行（E077）→ 构建树内的 `flex` 与安装后的 `reflex`/`reflex++` 均已自签，实测可运行 |
| 消费者链路 | PASS | C 与 C++ 两条「生成 → 编译 → 链接 → 运行 → 断言」链路均通过（见上 T6/T7） |

### 依赖

- 构建期（`tool_requires`）：`bison/3.8.2`（Makefile 的 `YACC = bison -y`）、
  `diffutils/3.12`（`make check` 用 `cmp` 逐字节比对）。
- 运行期：**零依赖**（`librefl.a` 静态自足）。

## 补充说明

### 遇到的问题与解决方案

1. **`config.guess` 无法识别 HongMeng 内核** → 显式传
   `--build=aarch64-linux-ohos --host=aarch64-linux-ohos`；两者 canonical 后相等故
   `cross_compiling=no`，`@no_cross@` 守卫打开，`make check` 才会真正执行（否则会被静默跳过）。

2. **本包修复的上游缺陷：C++ 扫描器全部无法编译**。骨架把 C-only 的
   `static int yy_init_globals(void)` 与 `int yylex_destroy(void)` 排在 non-C++ 守卫区块
   （骨架标记 `%-` … `%*`）**之外**；C++ 模式下这两个名字是 `yyFlexLexer` 的成员而非文件级
   全局，于是 `reflex -+` / `reflex++` 生成的一切 C++ 扫描器报 10 处
   `use of undeclared identifier 'yy_current_buffer' / 'yy_c_buf_p' / 'yy_init' / 'yy_start' /
   'yyin' / 'yyout'`。补丁 `0001-skel.c.patch`（+3 行，`patch_type: bugfix`，
   **非平台专用**）用骨架自带的守卫标记把两函数包回 non-C++ 区，C 路径输出逐字节不变。

3. **补丁必须打在 `skel.c` 而不是 `flex.skl`，且依赖 mtime 确定性**。发布包内
   `skel.c` 与 `flex.skl` **内容不一致却 mtime 相同**（均为 `2025-01-01 05:56`）：`skel.c`
   写 `(char *) 0`，`flex.skl` 写 `NULL`。mtime 相等时 make 不触发 `skel.c: flex.skl`
   规则 ⇒ 真正生效的构建输入是发布版 `skel.c`。若把补丁打在 `flex.skl` 上，`make check`
   会因重新生成的 `scan.c` 与 `initscan.c`（`(char *) 0`）不一致而失败。故：补丁打
   `skel.c`，并在 `build()` 用 `os.utime(skel.c, None)` 强制它比 `flex.skl` 新，
   防止 `mkskel.sh` 回写覆盖补丁（去掉这一步，修复会随构建顺序时有时无）。

4. **上游 `bigcheck` 目标本身不可用（已排除，非本包引入）**：其首项是裸 `-C`，本版
   选项解析器会把紧随其后的独立参数当作压缩后缀，报 `./flex: unknown -C option '/'`。
   本 PR 只驱动其余 6 种可用模式，并在 `test_package/MANIFEST.yml` 记录排除理由。

5. **C++ 消费者必须用 stdout 形式**：`reflex++ -t foo.l > foo.cc`。用 `-o foo.cc` 时
   `#include <reFlexLexer.h>` 由 `src/main.c` 的 `outn()` 在输出文件重定向前写入 stdout
   而丢失，生成物缺少类声明无法编译。该约束已写入 `notes.md` 与消费者用例 T7。

6. **消费者测试脚本不得使用裸命令名**：本机 `subprocess` 走 `posix_spawn` 快路径、
   不做 PATH 查找，`["sh", "-c", "command -v nm"]` 会直接 `FileNotFoundError: 'sh'`
   （首次 `conan-verify` 即因此单点失败）。已改为「显式绝对路径（profile 下发）→
   已知绝对路径候选 → `shutil.which`（纯 Python）→ 裸名兜底」的解析顺序。

7. **CI 上暴露的一类 HMDFS 问题：`config.status` 写不进自己刚建的临时目录**。首次推 PR 后
   CI 在 `conan-build-test` 失败（本地四道门禁全绿），失败日志（构建 #65023 / worker CI-015）：
   ```
   ./config.status: line 244: /storage/Users/currentUser/.cache/tmp/cslDeidH/subs.sed: Permission denied
   ./config.status: line 365: .../cslDeidH/subs.frag: Permission denied
   ./config.status: line 553: .../cslDeidH/out: Permission denied
   ./config.status: line 690: .../cslDeidH/undefs.sed: Permission denied
   grep: install-man: No such file or directory
   ```
   **性质说明（重要，勿误读为"必现"）**：同一 PR 的另一次构建（#65046 / worker CI-003）在
   **修复前的同一份代码**上却**通过**了（评论明确标注构建包为 `archives/r/reflex/20241231`
   且全部步骤 ✅），且该 PR 首轮的 #65021 失败于 `git-clone`
   （`cannot exec 'git-remote-https'`），属 worker 基础设施问题、与本节无关。因此这是
   **时序相关的间歇竞态**（HMDFS 新目录权限元数据的生效延迟），而非确定性必现 ——
   重试有可能"蒙对"，但根因真实存在且已从根因消除，不应依赖重试。

   根因：`config.status` 用 `umask 077 && mktemp -d -q "$TMPDIR/csXXXXXX"` 建目录后**立刻**
   重定向写入（`>"$tmp"/subs.sed`）；CI worker 上该次构建进程的 `TMPDIR` 落在 **HMDFS 用户卷**
   （`$HOME/.cache/tmp`，不是 worker 自身导出的 `/data` 路径），而 HMDFS 新建目录的属主/权限
   元数据尚未对该调用者生效 ⇒ 第一次写入即 EACCES。`configure` 自身反而通过（它用的是另一套
   临时文件路径），故症状酷似"构建中途随机崩"；本地 `TMPDIR` 恰好在 `/data` 缓存上，完全复现
   不了。修法双保险（不依赖时序）：
   - 补丁 `patches/0002-configure-hmdfs-tmpdir.patch`（`patch_type: portability`，平台专用）：
     去掉 `umask 077` 依赖，并在临时目录创建后显式 `chmod 700 "$tmp" 2>/dev/null || true`
     （`mktemp -d` 本就申请 `0700`，只是让权限位确定生效；该行随 heredoc 一并流入生成的
     `config.status`，实测生效于 `config.status:239`）。
   - recipe `_pin_tmpdir()`：`configure` 之前把 `TMPDIR`/`TMP`/`TEMP` 钉到经
     「建目录 → 立刻写入该目录内文件 → 回读」**写探针**验证的可写根（优先非 HMDFS 的
     `/data/storage/el2/base/cache`；候选全不过时保留原值并告警，不抛错）。
     实测构建日志：`Using usable TMPDIR=/data/storage/el2/base/cache`。
   - `test_package/test_reflex.py` 的 `_workdir()` 同样探针化（生成物、`.o` 与链接出的消费者
     程序都落在那个临时目录里）。
   修复后本地 `conan create` 全量复跑仍全绿（`Check successful` ×7 + `SMOKE-SUMMARY 7/7`）。

### 同名混淆提示

本包是 **Thomas Dickey 的 REFLEX**（版本号为日期式 `20241231`），**不是**
`cespare/reflex`（Go，其版本号恰好是 0.3.2），**也不是** Genivia RE/flex（C++，
本仓内另有 `archives/r/re-flex/6.3.0`）。三者谱系与产物完全不同，请勿合并审阅。

### 预检（preflight）取证说明

本 PR 含软件级 `archives/r/reflex/{README.md,commands.json,manifest.yaml}`
（R38 要求产可执行文件的包声明软件级 `commands.json`，仓内同类先例充分；软件级
`README.md`/`manifest.yaml` 亦为仓内既有惯例），因此 **PF9「变更路径缺版本目录层」必然命中**。

以 `origin/main` 为基线实跑取证（PF1–PF8 均无输出 = 全部通过）：

```bash
python3 scripts/ohc/preflight.py "$PWD" origin/main HEAD
# 唯一输出：
# ✗ PF9 分支/路径闸: 变更路径缺版本目录层（须 archives/<字母>/<包>/<版本>/<文件>）
#     : archives/r/reflex/README.md, archives/r/reflex/commands.json, archives/r/reflex/manifest.yaml
```

故本 PR 用 `--no-preflight` 创建：**PF1–PF8 已逐项实测通过，仅 PF9 因上述软件级文件命中**。
另：`conandata.yml` 的 `sources.url` 为单一官方 https（`invisible-island.net`），
无镜像/代理/`file://` 残留。

### 归档完整性

本包 `finish` 的 W3 本地 CI 模拟已通过（阻塞门禁），产出 `.ci-result.json`；
W4 Pre-PR 独立审计 verdict = pass（仅 1×P2 + 2×P3 提示，无 P0/P1）。

### 本 PR 的门禁执行记录（含 CI 迭代）

| 阶段 | 结果 |
|------|------|
| `lang-preflight` | PASS（task=cpp，detected=c，视为匹配） |
| `conan-verify`（G0–G4 + L2/L4/L5） | PASS（含补丁 0002 与 `_pin_tmpdir()` 的复跑，`Check successful` ×7） |
| `submit` → W3 本地 CI 模拟 | PASS，`JC_RESULT=pass`（无杂项文件、无二进制、单软件原子性合规） |
| W4 Pre-PR 独立审计 | PASS（verdict=pass，1×P2 + 2×P3） |
| Preflight | PF1–PF8 通过；PF9 因软件级文件必然命中（见上节取证），`--no-preflight` 创建 |
| 远端 CI（GitCode） | 首轮 #65021 失败于 `git-clone`（worker 基础设施，`cannot exec 'git-remote-https'`）；#65023 失败于 `conan-build-test`（HMDFS `config.status` EACCES，见补充说明第 7 条）；#65046 **通过**（修复前代码，印证其为间歇竞态）→ 已从根因修复并重推、重触发 |
| 本地门禁 vs 远端 CI | ⚠️ 本地四道门禁（`conan-verify`/W3/W4/`junk_check`）在**同一份代码**上全绿，却仍漏掉了本次缺陷 —— 属"宿主环境差异"维度（CI 的 `TMPDIR`/`HOME` 解析与本地不同），已沉淀为踩坑清单 #41 |
