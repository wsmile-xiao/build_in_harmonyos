# GNU config.guess/config.sub 两代格式差异——OHOS patch 必须按版本匹配

> Draft: DRAFT-AUTOTOOLS-CONFIG-GUESS-TWO-GENERATION-FORMATS
> Stem: `DRAFT-autotools-config-guess-two-generation-formats` — pairs with the same-stem `.kv`
> 来源：util-linux 2.42（PR #9262，新版格式）+ lttng-ust 2.15.1（PR #9284，旧版格式），2026-09-10

## 基本信息

- **ID**: DRAFT-AUTOTOOLS-CONFIG-GUESS-TWO-GENERATION-FORMATS
- **严重度**: 3
- **类别**: autotools, config.guess, config.sub, portability, conan-recipe, OHOS
- **触发工具**: autoconf|config.guess|config.sub|configure|conan
- **阶段**: configure

## 错误特征

```
configure: error: ... config.sub aarch64-unknown-linux-ohos failed|
configure: error: cannot run ... config.sub|
config.sub: line NNNN: syntax error near unexpected token `newline'|
（patch 静默不命中——日志无 "patched config.sub" 输出但 configure 仍失败）
```

## 可复现问题

GNU config.guess/config.sub 有**两代格式**，OHOS 适配 patch 的字符串锚点完全不同：

- **旧版**（2023 前，如 lttng-ust 2.15.1）：
  - config.guess aarch64 分支：`aarch64:Linux:*:*)\n\tGUESS=$UNAME_MACHINE-unknown-linux-$LIBC\n\t;;`
  - config.sub kernel-os 组合：`linux-gnu* | linux-dietlibc* | linux-android* | linux-newlib* \`（**无 `-` 结尾**）
- **新版**（2024+，如 util-linux 2.42）：
  - config.guess aarch64 分支：`aarch64:Linux:*:*)\n\tset_cc_for_build`（CPU/LIBCABI 变量）
  - config.sub kernel-os 组合：`linux-gnu*- | linux-android*- | linux-dietlibc*- | linux-llvm*- \`（**带 `-` 结尾**）

同一份 OHOS patch 模板：按新版格式写的 `linux-gnu*-` 锚点在旧版 config.sub 上**静默不命中**（日志无 "patched" 输出、configure 仍报 config.sub 失败）；反之亦然。util-linux 2.42（新版）与 lttng-ust 2.15.1（旧版）正好构成完整对照——两份配方各需不同格式的 patch。

另注意两个通用坑（两代通用）：
1. **config.guess/config.sub 可能不在顶层**——util-linux/lttng-ust 在 `config/` 子目录，c-ares 也在 config/；需按实际位置 patch
2. **config.sub 插入行必须带 `\` 续行符**——在 `zephyr* \` 后插入 `| ohos*` 若缺尾 `\`，case 语句语法错误（`syntax error near unexpected token 'newline'`）

## 根因分析

GNU config.guess 在 2023-2024 间重构：aarch64 Linux 分支从简单的 `GUESS=$UNAME_MACHINE-unknown-linux-$LIBC` 改为 `set_cc_for_build` + CPU/ABI 细分检测；config.sub 的 kernel-os 组合从 `linux-gnu*`（裸通配）改为 `linux-gnu*-`（带 `-` 结尾的精确匹配）。OHOS patch 若用死字符串锚点，跨代即失效——**patch 必须按源码实际版本匹配格式**，且验证"patched"日志输出。

## 推荐方案

**方法**: version-matched-config-patch

**说明**: >
  (1) **先看实际格式再 patch**：`grep -nE "aarch64:Linux|GUESS=|set_cc_for_build" config.guess`
      与 `grep -nE "linux-gnu" config.sub`——确认新旧代；
  (2) **锚点按代选择**：旧版用 `GUESS=$UNAME_MACHINE-unknown-linux-$LIBC` 分支插入
      OHOS case；新版用 `set_cc_for_build` 前插入 case；
  (3) **config.sub 两代都要改两处**：os 合法性列表（`zephyr*` 附近，旧版 `zephyr*)`
      单行/新版 `zephyr* \` 续行）+ kernel-os 组合（旧版 `linux-gnu*`/新版
      `linux-gnu*-`）；**插入行必须带 `\` 续行符**；
  (4) **验证 patch 命中**：build 日志必须有 "patched config.guess/config.sub" 输出，
      否则 configure 报 config.sub 失败时先怀疑锚点未命中；
  (5) **config/ 子目录**：util-linux/lttng-ust/c-ares 的 config.guess/config.sub 在
      config/ 子目录，patch 路径按实际位置。

**验证/命令**:
```
grep -nE "GUESS=\$UNAME_MACHINE|set_cc_for_build" config/config.guess   # 判新旧代
grep -nE "linux-gnu\*|linux-gnu\*-" config/config.sub                  # 判新旧代
# patch 后：build 日志应含 "patched config.guess: OHOS platform recognition"
```

## 关键词

config.guess, config.sub, 两代格式, GUESS=, set_cc_for_build, linux-gnu*,
linux-ohos, 续行符, config/ 子目录, autotools, OHOS, util-linux, lttng-ust,
aarch64-unknown-linux-ohos, portability, conan
