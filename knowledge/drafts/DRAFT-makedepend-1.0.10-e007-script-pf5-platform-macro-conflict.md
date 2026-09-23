# DRAFT-makedepend-1.0.10-e007-script-pf5-platform-macro-conflict — E007 官方补丁脚本产出的 `__OHOS__` 会被 PF5 平台宏闸拦在建 PR 之前

> **Contributor**: OpenDesk (K4T9) | **Status**: DRAFT | **Updated**: 2026-09-12
> **Severity**: high | **Category**: framework / patch / review-gate
> **Audience**: 所有 autotools 适配（E007 config.guess/config.sub 补丁）的执行者

## 问题（Symptom）

按 E007 的推荐方案（官方脚本）生成 config.guess 补丁后，`ohc-run.py submit` 在建 PR 前的
PF5 硬闸被拦截，PR 根本建不起来：

```text
PF5 平台宏闸（R8 前置）：patches/*.patch 新增行禁 __OHOS__
（例外如 libc 探针须在 PR 说明理由）
```

矛盾点：**被拦的 `__OHOS__` 正是官方脚本自己插入的**。

## 根因（Root Cause）

1. `scripts/patch-autotools-ohos.pl` 第 36-48 行在 `__ANDROID__` libc 探测后强制插入
   `#elif defined(__OHOS__) / LIBC=ohos`；第 127 行还把 `$gc =~ /__OHOS__/` 当作
   "config.guess 打补丁成功"的校验条件之一（第 133-134 行打印 `__OHOS__=%d`）。
2. PF5 平台宏闸（SKILL.md §3 preflight，R8 前置，v12.17 新增 / v12.20 扩面）
   对 `patches/*.patch` 的**新增行**禁 `__OHOS__`；只有**上下文行**与**存量**豁免。
3. 仓内 628 个含 `__OHOS__` 的补丁全部是 v12.17 之前落地的存量；新 PR 不享有豁免
   → **照 E007 官方脚本做 = 必被拦**。

关键事实：该段对 OHOS 原生目标**并不生效**。HarmonyOS 的 `uname -s` 返回 `HarmonyOS`，
不会进入 `case $UNAME_SYSTEM in Linux|GNU|GNU/*)` 分支（该分支只处理 uname 报 Linux 的场景），
真正起作用的是脚本第 2 处新增的 `*:HarmonyOS:*:*` 分支（输出 `aarch64-unknown-linux-ohos`）。

## 附带收窄结论：config.sub 的三处修改不是普适必需

E007 文档把"config.sub 三处修改"写成了通用动作，但实测 makedepend 1.0.10 自带的
config.sub（timestamp `2024-05-27`）**已内置 ohos**：

```console
$ sh config.sub aarch64-linux-ohos
aarch64-unknown-linux-ohos          # 原生接受，rc=0
$ grep -n 'ohos\*' config.sub       # OS 白名单已含 ohos*
2070:	| ohos* \
$ grep -n 'linux-ohos\*' config.sub # 内核-OS 组合校验已含 linux-ohos*
2213:		    | linux-relibc*- | linux-uclibc*- | linux-ohos*- )
```

官方脚本本身也是幂等的（`unless ($sc =~ /ohos-linux/)` 才插入）。正确顺序应是
**先验证 config.sub 是否已支持，再决定改不改**，而不是无条件补三处。

## 本次实测证据（makedepend 1.0.10，2026-09-12，OHOS aarch64）

| 步骤 | 结果 |
|---|---|
| 脚本式补丁（含 `__OHOS__` LIBC 段） | 预判命中 PF5（新增行 `+#elif defined(__OHOS__)`） |
| 删除该段、只保留 `*:HarmonyOS:*:*` 分支 | `sh config.guess` → `aarch64-unknown-linux-ohos`（rc=0）；`patch -p1 --dry-run` rc=0；应用后与手工改好的源码 `diff -rq` 为空 |
| 删除后完整 `conan create`（CI 同源 profile） | rc=0；`Apply patch (portability)`×2；`make check` **PASS 2/2**；test_package 4 项断言全过 |
| 只补 config.guess、不补 config.sub | configure 正常完成（`config.status: creating Makefile / makedepend-config.h`），无 `OS ohos not recognized` |

## 查重差异（为何新增）

| 既有条目 | 主题 | 差异 |
|---|---|---|
| E007（正式） | config.guess 缺 HarmonyOS 分支的**错误特征与脚本用法** | 未涉及 PF5 门禁；也未区分 config.sub 是否已内置 ohos |
| DRAFT-autotools-config-guess-two-generation-formats | config.guess 跨代格式差异（补丁锚点必须匹配源码版本） | 讲**锚点格式**，不讲平台宏与门禁冲突 |
| DRAFT-E564-oldstyle-config-guess-ohos-reanchor | 老式 config.guess 的 OHOS 锚点重定位 | 同上，不同根因 |
| DRAFT-postgresql-18.3-config-sub-ohos-native-build | 自带 config.sub 已识别 ohos + 显式传 `--build` 可跳过 config.guess | 讲"无需外置拷贝"，未讲 PF5 与补丁最小化 |

结论：**"官方推荐路径的产物被自己的新增门禁拦截"**这一结构性冲突，以及
"config.sub 需先验证再补"的收窄口径，知识库无既有条目。

## 方案（Recovery）

**方案 1（推荐，零门禁摩擦）——补丁最小化：只补真正需要的分支，删掉 `__OHOS__` LIBC 探针段。**

```bash
# 只保留 HarmonyOS 平台分支，不引入平台宏
# config.guess: 在 `case $UNAME_MACHINE:$UNAME_SYSTEM:...` 处新增
#     *:HarmonyOS:*:*) ... GUESS=${MACHINE}-unknown-linux-ohos ;;
# 验证（每次都要跑）
sh config.guess                      # 期望 aarch64-unknown-linux-ohos
sh config.sub aarch64-linux-ohos     # 期望 aarch64-unknown-linux-ohos（已支持则跳过 config.sub 修改）
patch -p1 --dry-run < patches/0001-config.guess.patch
```

**方案 2（必须保留平台宏时）——按 R8 例外申报。**
在 PR 描述里说明这是 libc 探针用途（R8 明文允许"例外如 libc 探针，须在 PR 说明理由"），
并说明为什么不能删（例如目标场景确实存在 uname 报 Linux 的 HarmonyOS 环境）。

## 禁止事项（forbid）

- ❌ 为过闸而改动 `ci/scripts/junk_check.sh` / preflight 白名单（框架文件，须单独 PR）
- ❌ 在 PR 里悄悄 `--no-preflight` / `OHC_PREFLIGHT=0` 绕过（自担风险且失去门禁保护，需显式声明）
- ❌ 顺手改 E007 文档/脚本本体来"对齐"（框架修改须单独 PR）
- ❌ 直接照搬其他包的补丁而不验证锚点与适用性（跨代 config.guess 格式不同）
