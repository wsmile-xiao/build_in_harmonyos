# DRAFT-autotools-config-sub-silent-ohos-triplet — 只补 config.guess 时 config.sub 会把 OHOS 三元组**静默**规范化成 `<machine>-unknown-linux-gnu-ohos`（configure/make 全绿，host_os 却是 `linux-gnu-ohos`）；并澄清 Conan 何时才注入 `--host/--build`

> **Contributor**: Awstme | **Status**: DRAFT（最终编号由知识库主编确认） | **Updated**: 2026-09-11
> **Severity**: 2 (silent-false-green) | **Category**: autotools / config.sub / config.guess / conan / ohos / native-build
> **Audience**: 在 OHOS 上用 Conan 适配自带 configure 的 autotools 包的配方维护者；以及维护 E007/E122 的人

## 触发（trigger）

- OHOS 上适配 autotools 包，按 E007 补了 `config.guess` 的 HarmonyOS 分支，**没有**同步补 `config.sub` 的
  `linux-ohos` 白名单（或补了但没核验规范化结果）。
- 配方用 Conan `AutotoolsToolchain` + `Autotools`。

## 症状（symptom）

**没有报错**。configure 绿、make 绿、产物能跑，只有三元组是错的：

```
$ sh acscripts/config.guess
aarch64-unknown-linux-ohos                       # config.guess 补丁正常工作
$ sh acscripts/config.sub aarch64-unknown-linux-ohos
aarch64-unknown-linux-gnu-ohos                   # ← 静默规范化，rc=0，无任何告警
$ ./configure --prefix=$P
configure rc=0
checking build system type... aarch64-unknown-linux-gnu-ohos
checking host system type... aarch64-unknown-linux-gnu-ohos
checking whether we are cross compiling... no
$ make -j1 && ./src/digup -V
make rc=0 ; digup 0.6.57                        # 产物可用，缺陷完全不可见
$ grep -o 'S\["host_os"\]=[^ ]*' config.status
S["host_os"]="linux-gnu-ohos"                     # 错误平台身份落盘
# 注意：config.status 不是 shell 赋值语法，`grep '^host_os=' config.status` 会 rc=1 且无输出，
# 照抄该写法会把「命令没匹配到」误读成「平台身份正常」
```

对比：同一棵树里若 Conan 传入无 vendor 段的 `aarch64-linux-ohos`，config.sub 会**响亮**报错
`Invalid configuration `aarch64-linux-ohos': system `ohos' not recognized` —— 即
「有没有错误」取决于三元组来自哪条路径，只有 `config.guess` 那条路径是静默的。

## 机制（root cause）

以 digup 0.6.57 自带的 GNU config 脚本（`timestamp='2020-01-01'`）为例：

1. 该版 `config.sub` 有**两条**入口分支，取决于输入三元组是 3 段还是 4 段，而两条分支的白名单不同：

   | 输入 | 走哪条分支 | 由哪个 hunk 修正 |
   | --- | --- | --- |
   | `aarch64-unknown-linux-ohos`（4 段，**config.guess 产出**） | `case $1 in *-*-*-*)`（`config.sub` 125-128 行，在 ambiguous 分支**之上**）→ `basic_machine=aarch64-unknown`、`os=linux-ohos` | **OS 列表 hunk（1357 行的 `-linux-gnu* \| -linux-android*` 行）** |
   | `aarch64-linux-ohos`（3 段，**Conan 注入形态**） | `*-*-*)` ambiguous 分支（129-150 行）→ `maybe_os=linux-ohos` 需命中 134 行的列表 | **两个 hunk 都要**：134 行列表缺失时它落进 `*)` 兜底被拆错；1357 行列表缺失时仍被静默改写 |

   隔离实验（把补丁 0002 的两个 hunk 拆开分别应用）：

   ```
   只应用 134 行那个 hunk：4 段 → aarch64-unknown-linux-gnu-ohos（静默错）；3 段 → aarch64-unknown-linux-gnu-ohos（静默错）
   只应用 1357 行那个 hunk：4 段 → aarch64-unknown-linux-ohos（正确！）；3 段 → Invalid configuration ... system `ohos' not recognized（响亮 rc=1）
   两个 hunk 都应用    ：4 段 → aarch64-unknown-linux-ohos；3 段 → aarch64-unknown-linux-ohos   （均正确）
   ```

   真正的静默改写来自 1357 行所在 OS 列表的兜底分支 `os=\`echo $os | sed -e 's|linux|linux-gnu|'\``
   （1397 行）：白名单没放行时它把 `os` 改写成 `<kernel>-<libc>-<os>` 形态，**rc 仍为 0**。
   规范化结果被 configure 全盘采信（`host`/`build`/`host_os`），并写入 `config.status`、`config.h`。

   ⚠️ 因此「只补一个 hunk 就够了」是错的：只补 134 行那个会让 **4 段形态仍然静默错误**
   （正好是本条要防的情形）；只补 1357 行那个会让 3 段形态响亮失败而 4 段形态正确。
   两个 hunk 必须同时存在，并以 `config.sub "$(config.guess)"` 原样返回作为验收判据。
2. 无害与否取决于消费者：`host_os='linux-gnu-ohos'` 会被任何 `case $host_os in *-gnu*|linux-gnu*)`
   分支命中，`linux-ohos` 分支反而不会被命中。digup 自身只判 `*cygwin*|*mingw32*`，
   所以本包**功能上未受影响**；但这属于平台身份被判错，不是可以默认接受的差异。
3. 因此 `config.guess` 与 `config.sub` 的补丁必须**成对**且**互相核验**：
   `config.sub` 的输出必须等于 `config.guess` 的输出。只看「configure 是否通过」无法发现该缺陷
   （只补 0001 时 configure 一样通过）。

## 关于 Conan 的三元组注入：澄清与自我更正

早期版本的这条草稿（文件名 `DRAFT-conan-autotools-triplets-mask-config-guess`，未合入）主张
「Conan `AutotoolsToolchain` 默认**总是**注入 `--host/--build`，因此 `config.guess` 补丁是死代码，
必须在 `generate()` 里剪掉」。**该主张经独立审计与本轮实测证伪，现予撤回**，实测事实如下：

| 配置 | `AutotoolsToolchain.configure_args` | 结论 |
| --- | --- | --- |
| `-pr:h` 与 `-pr:b` 同一 OHOS profile（本仓库 CI：`ci/conan/build_and_test.sh` 把同一 `PROFILE_FILE` 传给两者） | `['--prefix=/', '--bindir=…', …]`，**无** `--host/--build` | Conan **不注入**；configure 自行调用 `config.guess`，补丁是生效路径；`update_configure_args({"--build": None, "--host": None})` 在此为**空操作**（trip-probe 配方实测剪枝前后 list 逐元素相同） |
| `-pr:b` 换成异构（如 Linux/x86_64）profile | `[..., '--host=aarch64-linux-ohos', '--build=x86_64-linux-gnu']` | Conan **注入**；此时剪掉三元组会让 configure 在**构建机**上跑 `config.guess` 并静默选到构建机架构，属危险操作，**不应**作为通用建议 |

机制：`conan/tools/gnu/autotoolstoolchain.py` 的三元组生成被
`if self._is_cross_building:` 包住，而 `_is_cross_building = not is_universal_arch and cross_building(self)`；
同构 profile 下 `cross_building()` 为 False，`_host/_build` 保持 `None`，`_get_triplets()` 的 `if value:`
不追加任何参数。（`tools.gnu:host_triplet` / `tools.gnu:build_triplet` 两个 conf 可显式覆盖。）

正确做法：**不要**为了「让 config.guess 生效」去剪三元组；让 `config.sub` 同时接受两种输入形态即可
——`config.guess` 产出的 4 段 `<machine>-unknown-linux-ohos`（由 OS 列表 hunk 放行）与 Conan 注入的
3 段 `<machine>-linux-ohos`（需 ambiguous 列表与 OS 列表两个 hunk 同时就位），
两处 hunk 都补齐后实测两种形态都规范化到 `aarch64-unknown-linux-ohos`。

## verification_cmd（可判定的自检，digup 0.6.57 / 2020-01-01 版脚本）

```sh
# 1) config.guess 与 config.sub 必须互相对齐（核心判据）
sh acscripts/config.guess                                   # 期望 aarch64-unknown-linux-ohos
sh acscripts/config.sub "$(sh acscripts/config.guess)"       # 必须原样返回同一串
# 只补 config.guess 时第二条返回 aarch64-unknown-linux-gnu-ohos（rc=0，无告警）
# 2) configure 落盘的平台身份
./configure --prefix=$P >/dev/null 2>&1 && grep -o 'S\["host_os"\]=[^ ]*' config.status
# 期望 S["host_os"]="linux-ohos"；错误形态为 S["host_os"]="linux-gnu-ohos"
# （configure 日志同样可断言：checking host system type... aarch64-unknown-linux-ohos）
# 3) Conan 注入条件（trip-probe：只打印 configure_args 的最小配方）
conan create . -pr:h="$OHOS_PROFILE" -pr:b="$OHOS_PROFILE"   # 期望无 --host/--build
conan create . -pr:h="$OHOS_PROFILE" -pr:b=./linux-x86_64    # 期望出现 --host=aarch64-linux-ohos --build=x86_64-linux-gnu
```

实跑（2026-09-11，HarmonyOS aarch64 / HongMeng Kernel 1.12.0，Conan 2.29.1）：

```
config.guess                                → aarch64-unknown-linux-ohos
config.sub aarch64-unknown-linux-ohos       → aarch64-unknown-linux-gnu-ohos   （补丁 0002 缺失时；rc=0）
config.sub aarch64-unknown-linux-ohos       → aarch64-unknown-linux-ohos       （补丁 0002 就位时）
config.sub aarch64-linux-ohos               → aarch64-unknown-linux-ohos       （Conan 注入形态）
仅 0001+0003 的树：configure rc=0 / make rc=0 / ./src/digup -V 正常 / S["host_os"]="linux-gnu-ohos"
同构 profile：ARGS_BEFORE == ARGS_AFTER（无三元组）；异构 profile：出现 --host/--build
```

## 适用边界（Applicability / Scope）

- 适用：所有自带（或 autoreconf 生成）GNU `config.guess`/`config.sub` 的 autotools 包，
  在 `uname -s` 不在 GNU 名单的平台上做适配；尤其适用于「按 E007 只补了 config.guess」的存量配方。
- 不适用：不使用 config.sub 的构建系统（CMake/Meson 的平台识别走各自工具链）。
- 边界：静默规范化的**后果**取决于消费者是否按 `host_os` 分支；若上游代码存在 `*-gnu*` 分支，
  必须按缺陷处理；若上游只用它做记录（如 digup），影响面为平台身份不准确，也应修正而非忽略。
- 边界（注入）：剪掉 Conan 三元组**只在 `build == host` 时**安全；异构 profile 下剪枝会让 configure
  在构建机上判定平台。

## 与既有条目查重差异（Dedup / Delta vs Existing Entries）

- **E007**：config.guess 不识别 HarmonyOS、须打补丁，并禁止用 `--build/--host` 绕过。
  本条不重复该结论；增量是「打完后如何**验证**补丁真的生效、以及漏补 config.sub 的静默后果」。
- **E122**：要求 config.sub 补 `linux-ohos` 到 kernel-os 校验列表，其错误签名是**响亮**的
  `not known to work with OS ohos`。本条的增量是该缺陷的**静默形态**：rc=0 + 三元组被规范化成
  `linux-gnu-ohos`，与 E122 描述的失败方向相反，需用不同判据发现。
- **DRAFT-E564-oldstyle-config-guess-ohos-reanchor**：讲旧式脚本的**补丁锚点**；
  本条讲补丁**输出是否被下游脚本改写**，正交且互补。
- **DRAFT-config-guess-era-echo-exit**：讲旧式脚本的**分支形态**（echo+exit vs `GUESS=`）；
  本条引用其代际判据但不重复结论。
- **撤回条目** `DRAFT-conan-autotools-triplets-mask-config-guess`（本 PR 前一版本，未合入）：
  其「Conan 总是注入三元组 → config.guess 补丁是死代码」的结论不成立，已由本条取代；
  若主编已收到该名称的条目，请以本条为准。

## 证据（evidence）

- 静默规范化：`config.sub aarch64-unknown-linux-ohos → aarch64-unknown-linux-gnu-ohos`（rc=0）；
  仅 0001+0003 的树上 `configure` rc=0、`make` rc=0、`S["host_os"]="linux-gnu-ohos"`；
  `$HOME/tmp/digup-0.6.57/exp-h1only/{configure2.log,make.log}`
- Conan 注入条件：trip-probe 配方（只打印 `configure_args`）两轮实测
  `$HOME/tmp/digup-0.6.57/exp-args/`；同构 `ARGS_BEFORE==ARGS_AFTER`，异构出现 `--host/--build`
- 注入点：`conan/tools/gnu/autotoolstoolchain.py` `__init__` 的 `_is_cross_building` 分支与 `_get_triplets()`
- 修复与采信轮：`archives/d/digup/0.6.57/patches/000{1,2,3}-*.patch`、
  `archives/d/digup/0.6.57/reports/conan-create.log`（`checking build/host system type...
  aarch64-unknown-linux-ohos`、`checking whether we are cross compiling... no`）
- 独立证伪过程：W4 独立审计（同一 PR 的 `reports/audit-result.json`，P1 项即针对前一版草稿）

## 关系（relations）

- principles: P-AUTOTOOLS-001（禁止用三元组绕过平台识别）
- similar_to: E007, E122, DRAFT-E564-oldstyle-config-guess-ohos-reanchor, DRAFT-config-guess-era-echo-exit
- conflicts_with: 无
