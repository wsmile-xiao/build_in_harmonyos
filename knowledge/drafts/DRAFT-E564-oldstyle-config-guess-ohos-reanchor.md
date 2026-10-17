# DRAFT-E564 — 2012 旧式 config.guess/config.sub 的 OHOS 补丁需换锚点

## 现象 (What happened)

对 libicns 0.8.1（捆绑 2012 年版 GNU config 脚本）做 OHOS PC 原生构建时：

1. 未打补丁：`config.guess` 直接报 `unable to guess system type` 退出 1
   （本机 `uname -s` = `HarmonyOS` 无匹配分支）。
2. 按知识库 E007 的 `rec_command` 运行官方工具
   `scripts/patch-autotools-ohos.pl config.guess config.sub`：
   自检 **1/5 分**（仅 "HarmonyOS system identification" 一项 ok），
   三个锚点 warning 跳过，但**工具退出后不报错**；
   真机验证 `sh config.guess` 依然失败：
   `can't create /storage/.../cgiicNNf/dummy.c: Permission denied`
   → `unable to guess system type`。

## 根因 (Root cause)

新旧两代 GNU config 脚本风格断层（2016-08 上游重构引入 `GUESS=` 变量），
官方 perl 工具的 5 个锚点全部取自新式脚本：

| # | perl 工具锚点 | 旧式脚本 (2012) | 结果 |
|---|--------------|-----------------|------|
| 1 | `#if defined(__ANDROID__)` LIBC 块 | 无此块 | warn 跳过 |
| 2 | `*:NetBSD:*:*` case 前插入块 | 能命中，但生成代码用 `GUESS=` 赋值；旧式末尾无 `echo "$GUESS"` | **插入即坏**：赋值死代码 + 块内 TMPDIR 写测试在 $HOME 只读时 Permission denied |
| 3 | `android-linux)` 三行块 (config.sub) | 无此条目 | warn 跳过 |
| 4 | `linux-uclibc*)` 结尾括号 | 行尾是 `\` 续行 | warn 跳过 |
| 5 | 同上 | 同上 | warn 跳过 |

且旧式 `config.sub` 对 `linux-ohos` 需要**双锚点**，缺一不可：

- 只加 maybe_os 行（`knetbsd*-gnu* | netbsd*-gnu* | linux-ohos*`）：
  `aarch64-unknown-linux-ohos` 会被规范化成
  `aarch64-unknown-linux-gnu-ohos`，而 basic os 列表不认 `-gnu-ohos`，
  仍报 `Invalid configuration`。
- 必须**同时**在 basic os 列表行（`-linux-gnu* | -linux-android*` 行尾）
  追加 `| -linux-ohos*`。

## 解法 (Fix)

手工写 portability 补丁（本 PR `archives/l/libicns/0.8.1/patches/
0001-config-guess-ohos.patch`，已真机验证）：

1. **config.guess**（判别：`grep -c '^GUESS='` = 0 即旧式）：
   在 `aarch64:Linux:*:*)` 分支**前**插入：
   ```
       aarch64:HarmonyOS:*:*)
        echo ${UNAME_MACHINE}-unknown-linux-ohos
        exit ;;
   ```
   （旧式风格：直接 echo + exit，不用 GUESS 变量）
2. **config.sub** 双锚点：
   - maybe_os kernel-libc 分支：`knetbsd*-gnu* | netbsd*-gnu* | linux-ohos* | \`
   - basic os 列表：`-mingw32* | -linux-gnu* | -linux-android* | -linux-ohos* \`

## 验证 (Verification)

本机 HarmonyOS aarch64（HongMeng Kernel 1.12.0）：

```
$ sh config.guess
aarch64-unknown-linux-ohos
$ sh config.sub "$(sh config.guess)"
aarch64-unknown-linux-ohos          # 原样接受
$ sh config.sub aarch64-unknown-linux-gnu-ohos
aarch64-unknown-linux-gnu-ohos      # 规范化形式也接受（双锚点生效）
```

随后 `conan create`（G0–G4）+ scoped CI（L0/L1/L1e/L2/L4/L5）全部 PASS。

## 适用边界 (Applicability / Scope)

- 适用：捆绑 pre-2016 旧式 config 脚本的 autotools 包
  （libicns 0.8.1 实证；abook 0.6.1、nvi 1.81.6、acsccid 1.1.13 的已合入
  补丁同为旧式锚点风格，可交叉印证）。
- 不适用：新式脚本（`grep -c '^GUESS='` ≥ 1）——用 E007 的官方 perl 工具。
- 边界：perl 工具的 warning **不构成失败信号**，必须看自检分数与真机
  `sh config.guess` 输出；分数 <5/5 时禁止采信。

## 与既有条目查重差异 (Dedup / Delta vs Existing Entries)

- **E007**：同一问题域，但 `rec_command`（perl 工具）与验证命令均只覆盖
  新式脚本；本条补充旧式代际的判别方法与双锚点补丁锚点。
- **DRAFT-c-ares-lite-1.33.1**：`config/` 子目录布局 + 新式脚本（该包
  config.guess 有 GUESS 风格），其三处 config.sub 锚点与新式脚本一致。
- **DRAFT-postgresql-18.3**：走显式 `--build=` 跳过 config.guess 的路线；
  E007 `forbid_1` 禁止 `--build/--host` 绕过（误判交叉编译），本条与其
  不冲突——本条是"打补丁"正路的旧式补充。

## 参考 (References)

- 上游重构：config.guess "Rewrite using GUESS variable"（2016-08）
- 本 PR 实证：`archives/l/libicns/0.8.1/patches/0001-config-guess-ohos.patch`
- 旧式先例：`archives/a/abook/0.6.1/patches/0001-config.guess.patch`
