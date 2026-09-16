# DRAFT-bats-suite-ohos-runtime-shims — bats 上游测试套件在 OHOS 实跑：先判定桩机制，再补三个环境 shim

> **Contributor**: ohpcd | **Status**: DRAFT | **Updated**: 2026-09-11
> **Severity**: 🟡 medium | **Category**: testing / bats / bash / shim

## 相关既有条目（同族差异化定位）

| 既有条目 | 同族点 | 本 skill 的增量（差异化） |
|---------|--------|--------------------------|
| **E143 / E165** | 均为 `/usr/bin/python3`、`/bin/bash` 等**解释器/shebang 缺失** | 本条目是**测试框架装配**（bats + 三个运行时 shim），与 shebang 路径问题不同层 |
| **E272** | DejaGNU 套件的 `spawn -nottyinit` + libc `tmpfile()` shim | 同属"测试套件在 OHOS 跑不起来"，但框架不同（DejaGNU vs bats），且本条目核心是**先判定桩机制**这一方法论 |
| **DRAFT-ohos-execve-path-redirect-shim** | 同为"用 shim 补齐环境差异" | 该条在 **execve 层**重写硬编码路径；本条目在 **PATH 层**补缺失/行为不符的工具 |

> 查证（2026-09-11）：`bats`、`respond_to`、`egrep is obsolescent`、`md5cmd`、
> `busybox install`、`no-headers` 在 knowledge/doc 与 knowledge/drafts 下命中
> **各 0 条**——本条为空白领域。

## Scope（何时用）

在 OHOS 上运行 **bats（Bash Automated Testing System）** 驱动的上游测试套件时。
典型现象（按严重度排序）：

```
not ok 1 bats-gather-tests                 # ← 最严重：全部用例 0 运行
# (in file test/helpers.sh, line 10, ... `. test/helpers.sh' failed

BW01: `run`'s command `directory install foo` exited with code 127,
      indicating 'Command not found'        # ← 缺系统工具

not ok N ... `[[ -z ${output} ]]' failed    # ← 输出被警告污染
```

## 第一步（最关键）：判定测试是"真调外部命令"还是"桩替换"

**这一步决定通过率是 0 还是接近 100%，不做就会误判。**

纯 bash 工具的 bats 套件经常被想当然地判定为"依赖 brew/apt/dnf/npm/pip/sudo
等包管理器，OHOS 无法运行"。但很多套件使用**桩替换**——把外部命令映射到录制输出：

```bash
# test/type-brew.bats
. test/helpers.sh
brew () { . $BORK_SOURCE_DIR/types/brew.sh $*; }

setup () {
  respond_to "uname -s" "echo Darwin"
  respond_to "brew list --formula" "cat $fixtures/brew-list.txt"      # ← 桩！
  respond_to "brew outdated --formula" "cat $fixtures/brew-outdated.txt"
}

@test "brew status reports missing brew exec" {
  respond_to "which brew" "return 1"
  ...
}
```

**判定方法**：
1. 读 `test/helpers.sh`，找 `respond_to` / `mock` / `stub` 之类机制；
2. 看 `test/fixtures/` 是否存在（bork 有 33 个录制输出文件）；
3. 翻任一用例的 `setup()`——若命令被映射到 `cat $fixtures/...`，则**包管理器根本不被调用**。

→ 结论：桩替换型套件**必须实跑**，不能用"缺依赖"整体声明 0 通过率。

## 第二步：补三个 OHOS/Linux 行为差异 shim

三个 shim 都**不修改上游测试源码**，只在 `PATH` 前置：

### ① uname shim —— 决定"能不能跑"

bork 的 `test/helpers.sh` 第 10 行 `md5c=$(md5cmd $platform)`，而 `md5cmd` 只认
Linux/Darwin/FreeBSD：

```bash
md5cmd () {
  case $1 in
    Darwin|FreeBSD) ... ;;
    Linux) ... ;;
    *) return 1 ;;      # ← OHOS 的 uname -s 返回 HarmonyOS，走到这里
  esac
}
```

在 bats 的 `set -e` 语义下，`return 1` 直接令 `helpers.sh` 加载失败 →
**全部 366 个用例 0 运行**，报 `not ok 1 bats-gather-tests`。

```sh
#!/bin/sh
# shimdir/uname —— 仅伪装 -s，其余参数原样透传
if [ "$1" = "-s" ]; then echo Linux; else exec uname "$@"; fi
```

### ② egrep shim —— 决定"断言准不准"

OHOS grep 对 `egrep` 打印警告到 stderr：

```
egrep: warning: egrep is obsolescent; using grep -E
```

这污染了 bats 的 `[[ -z ${output} ]]` 断言（期望**空**输出），使 pipsi 类用例误失败。

```sh
#!/bin/sh
exec grep -E "$@"
```

### ③ install shim —— 决定"少数用例过不过"

OHOS 无 coreutils `install`（`command -v install` 为空），bork 的 `directory`
类型调用它得 127。**busybox 自带 install applet**，可转发（注意剔除 busybox
不支持的 GNU 专有选项如 `-C`/`--compare`）：

```sh
#!/bin/sh
args=""
for a in "$@"; do
  case "$a" in -C) ;; *) args="$args $a";; esac
done
exec busybox install $args
```

## 递进对照（必须做，用于证明每个 shim 真实生效）

| 阶段 | 结果 | 原因 |
|------|------|------|
| 无 shim | **0 运行**（`bats-gather-tests` 失败） | `md5cmd` 对 HarmonyOS `return 1`，set -e 下 helpers.sh 中断 |
| + uname shim | 361/366 | 框架恢复；egrep 警告污染 output 断言 |
| + egrep shim | 364/366 | pipsi 3 个用例恢复 |
| + install shim | **366/366** | directory 2 个用例恢复 |

> 没有递进对照，就无法区分"shim 生效"与"该用例本来就能过"，也无法解释通过率
> 变化的因果——这是最容易出错的地方。

## 运行

```sh
git clone --depth 1 https://github.com/bats-core/bats-core.git   # bats 无包时 vendoring
export BORK_SOURCE_DIR=<src>
export PATH=<shimdir>:$PATH
bats test/          # 或 make test
```

## 备选（fallback）

`record-running-baseline-and-failed-cases`：若补齐 shim 后仍有失败，逐条记录用例名、
失败断言、原始报错与已验证的 shim 覆盖范围——把"**已运行基线**（如实数字）"与
"剩余失败的具名原因"一并写入 manifest，而不是退回"无法运行"的整体声明。

## 禁止

- ❌ **"无 bats 故全部无法运行"**：bats 可 vendoring；桩替换机制下包管理器不被调用。
  不核实就声明 0 会低估适配质量，也会被审查方按"有可运行子集未尝试"打回。
- ❌ **改上游测试**（改 `.bats` 或 `respond_to` 使其通过）：越界（R6/R8），且掩盖真实差异。
- ❌ **PATH 注入后不做验证**：必须先单独验证 shim 生效（如 `uname -s` 输出 Linux），
  再做递进对照。

## 实证

- **bork/0.14.0（PR #8710）**：旧声明"0/366（bats 框架未安装 + 依赖系统包管理器）"
  经实跑更正为 **366/366（100%）**。递进数据：无 shim **0** → +uname **361** →
  +egrep **364** → +install **366**。
- 关键事实：上游测试全部用 `respond_to` 桩替换（`test/fixtures/` 33 个录制输出），
  从未真正调用 brew/apt/dnf/npm/pip。
