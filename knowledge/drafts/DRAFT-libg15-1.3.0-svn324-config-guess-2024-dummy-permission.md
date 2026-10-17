# DRAFT-libg15-1.3.0-svn324-config-guess-2024-dummy-permission — 现代 config.guess（2024-07-27）无 HarmonyOS 分支导致 dummy.c: Permission denied / cannot guess build type，本地通过与 CI 失败根因是 automake 工具链代际不一致

> **Contributor**: yanjiaxin / AtomCode | **Status**: DRAFT（最终编号由知识库主编确认） | **Updated**: 2026-09-24
> **Severity**: blocking (2) | **Category**: autotools / config.guess / conan / ohos / toolchain
> **Audience**: 在 OHOS/HMDFS 上通过 tool_requires automake 构建 autotools 包、遇到"本地通过但 CI 失败"的配方维护者

## 触发（trigger）

- 配方通过 `tool_requires("automake/1.18")`（+ libtool/2.5.4）提供构建工具链；bootstrap 里
  `automake --add-missing --copy` 安装的是 automake 1.18 自带的 **config.guess 2024-07-27**。
- 本地（有 $HOME/usr/local/bin 下的 automake 1.16）`conan create` 通过，但 PR CI
  （build_in_harmonyos，libg15 PR #11727 / CI #59402）在 `[conan-build-test]` 步骤失败。
- 完整报错落在 configure 的 `checking build system type`：
  ```
  config.guess: line 1613: /storage/Users/currentUser/.cache/tmp/cglKcjiL/dummy.c: Permission denied
  config.guess: unable to guess system type
  ...
  config.guess timestamp = 2024-07-27
  UNAME_MACHINE = "aarch64"
  UNAME_SYSTEM  = "HarmonyOS"
  configure: error: cannot guess build type; you must specify one
  ```

## 症状（symptom）

签名是 E007 的 `unable to guess system type` / `cannot guess build type`，但多了一个前置的
`dummy.c: Permission denied`（stderr 形式 `config.guess: line NNNN: <path>/dummy.c: Permission
denied`）。**本条的诊断增量**是"本地通过、CI 失败"这一入口：同一份配方、同一条命令，两端结果相反，
根因不在配方逻辑而在构建工具链的代际差异。

## 机制（root cause）

1. **config.guess 分代**：2023-08-22 版（automake 1.16 捆绑）主 case **含** `*:HarmonyOS:*:*)`
   分支（aarch64 下直接 `GUESS=aarch64-unknown-linux-ohos`），脚本输出三元组后 exit，**不触碰
   dummy.c**；2024-07-27 版（automake ≥1.17 / 1.18 捆绑）主 case **删去了**该分支，HarmonyOS
   匹配不到任何分支。
2. **2024 版回退路径**：主 case 落空 → GUESS 为空 → 进入
   "No uname command or uname output not recognized" 段 → `set_cc_for_build` 用
   `(umask 077 && mktemp -d "$TMPDIR/cgXXXXXX")` 建临时目录（GNU/Toybox mktemp 强制 0700）
   → `cat > "$dummy.c"` 写临时文件。
3. **HMDFS 权限**：$TMPDIR（CI 上为 `$HOME/.cache/tmp`，共享缓存）有 setgid 继承；0700 临时目录
   setgid 后 → 2700，属主/组与构建进程（USER=100）不一致 → `dummy.c: Permission denied`
   （E112 同族：共享目录 0700 跨 UID 不可写）。即便临时目录可写，2024 版也没有 HarmonyOS 分支，
   最终仍会报 "unable to guess system type"——两重问题。
4. **本地/CI 工具链差异（关键增量）**：本地 PATH 命中 `$HOME/usr/local/bin/automake`（1.16，
   其 config.guess 2023-08-22 已带 HarmonyOS 分支）→ 直接输出三元组 → 通过；CI worker
   （USER=100）因 E443（该目录文件 0770 属主跨 UID 不可执行）用不上它，automake 解析到
   tool_requires automake/1.18 → 2024 原版 config.guess → 失败。

## 解法（Fix）

bootstrap 之后、configure 之前，在**生成的** `config/config.guess` 主 case 的 esac 前注入
现代 GUESS= 形态的 HarmonyOS 分支（2024 版脚本末尾有统一 `echo "$GUESS"` 出口，GUESS= 赋值即
生效并直接退出，完全不触碰 dummy.c 临时目录）：

```sh
    *:HarmonyOS:*:*)
	case "$UNAME_MACHINE" in
	    aarch64|arm64) MACHINE=aarch64 ;;
	    armv7*|armv8*) MACHINE=arm ;;
	    x86_64|amd64)  MACHINE=x86_64 ;;
	    i?86)          MACHINE=i686 ;;
	    *)             MACHINE="$UNAME_MACHINE" ;;
	esac
	GUESS=${MACHINE}-unknown-linux-ohos
	;;
```

- 注入锚点：主 case 的 `esac` 紧跟唯一注释 `# Do we have a guess based on uname results?`，
  在该注释前插入；回退锚 `    *:NetBSD:*:*)\n`。
- guard：`grep -c HarmonyOS config.guess > 0` 时跳过（本地已补分支的场景）。
- **config.sub 2024 已认 linux-ohos**（OS 列表 `| ohos*`、kernel 列表 `| linux-ohos*-`，
  `sh config.sub aarch64-unknown-linux-ohos` 原样接受），无需改动。
- 配方落地示例：libg15 1.3.0-svn324 的 `conanfile.py::_fix_config_guess_ohos()`（build()
  里 `_generate_configure()` 后调用），与既有的 `_fix_configure_umask()`（config.status 的
  subs1.awk 权限修复）同型。

## 验证（Verification）

本机 HarmonyOS aarch64（HongMeng Kernel 1.12.0），三组实证（2026-09-24）：

```
# 1. 副本级：2024-07-27 config.guess + 注入 + 只读 TMPDIR
cp <automake-1.18-pkg>/share/automake-1.18/config.guess cg
#    （注入上述分支后）
TMPDIR=/tmp sh cg        # /tmp 为 erofs 只读
#    → aarch64-unknown-linux-ohos, rc=0, 无 stderr（未触碰临时目录，证明短路生效）

# 2. CI 等价：强制 conan automake/1.18 工具链（本地 profile 去掉 $HOME/usr/local/bin PATH）
conan create . -pr:h=ci-sim-ohos-aarch64 -pr:b=ci-sim-ohos-aarch64 --build="libg15/*"
#    → RC=0；构建产物 config/config.guess timestamp=2024-07-27 且含 HarmonyOS 分支；
#      configure result: aarch64-unknown-linux-ohos；test_package 断言 2/2 通过

# 3. 标准 profile（automake 1.16）回归
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
#    → RC=0（guard 跳过注入，无回归）
```

## 适用边界（Applicability / Scope）

- 适用：tool_requires automake ≥1.17（config.guess 2024-07-27 起）在 OHOS/HMDFS 上构建的
  autotools 包；判别 `grep -c HarmonyOS config.guess` = 0。E007 官方
  `scripts/patch-autotools-ohos.pl` §1.2 注入的正是现代 GUESS= 形态，对新式脚本可复用。
- 不适用：本地 automake 1.16 已带分支的场景（guard 跳过）；旧式（pre-2016、无 `echo "$GUESS"`
  尾部出口）config.guess——那是 DRAFT-E564 / DRAFT-config-guess-era-echo-exit 的范畴，
  需 echo+exit 形态。
- 边界：本条目解决"本地通过/CI 失败"这类工具链代际差异；若两端都失败且脚本是旧式，走
  DRAFT-E564（换锚点）或 DRAFT-config-guess-era-echo-exit（echo+exit 形态）路线。

## 与既有条目查重差异 (Dedup / Delta vs Existing Entries)

| 条目 | 覆盖点 | 本条目增量 |
|------|--------|-----------|
| E007 / E160 | 现代 config.guess 需加 HarmonyOS 分支（patch-autotools-ohos.pl） | 明确 2024-07-27 版**无**该分支的具体行为（dummy.c: Permission denied 前置错误）；把失败归因到 tool_requires automake 代际差异 = 本地通过/CI 失败 |
| DRAFT-E564 | 旧式（2012）脚本 + perl 工具换锚点失败 | 本条目是新式（2024）脚本 + tool_requires 工具链差异，注入形态为 GUESS=（而非 echo+exit）；config.sub 2024 无需双锚点 |
| DRAFT-config-guess-era-echo-exit | 2006/07 年代脚本 GUESS= 注入失效需 echo+exit | 本条目覆盖 2024 现代脚本，GUESS= 注入直接生效 |

---
*草稿流程：贡献者提交 DRAFT 到 knowledge/drafts/（.kv + .md 成对），正式 E 编号由知识库主编审核后入库；不得直接写入 knowledge/graph/。*
