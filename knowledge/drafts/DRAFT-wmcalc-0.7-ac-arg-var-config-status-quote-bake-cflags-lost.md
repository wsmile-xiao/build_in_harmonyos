# DRAFT: AC_ARG_VAR 值走 configure 命令行 ⇒ 引号被 config.status 烘进 Makefile，整组 `-I` 被静默丢弃

- **触发实例**：wmcalc 0.7 适配（任务 #11937，构建机 B，2026-09-27，worktree `~/qzy/主理-74-wmcalc-0.7`）
- **错误签名**：`fatal error: 'X11/Xlib.h' file not found`（而编译行里"看起来"有 `-I`）
- **类别**：autotools, pkg-config, quoting, build-env
- **严重度**：2（configure 照样通过，故障推迟到编译期，症状与真因相距两层；本包第 2 轮 `conan create` 因此白烧一轮）

## 症状

```text
第 1 轮 create：pkg-config 找不到 x11 → 显式给 X11_CFLAGS/XEXT_CFLAGS/XPM_CFLAGS 传值
第 2 轮 create：fatal error: 'X11/Xlib.h' file not found
                 但生成的 Makefile 里 AM_CPPFLAGS 展开后确实带着那串 -I
```

把命令行传值改成**环境变量**传值后，同一编译行立刻能解析到 conan 包内的 include 目录。

## 根因

autoconf 用 `AC_ARG_VAR` 声明的变量（`PKG_CHECK_MODULES` 会顺带声明 `X11_CFLAGS`/`X11_LIBS` 这类）有两条入口：

1. **configure 命令行参数**：值被写进 `config.status` 的替换表，然后**原样**展开到 `AC_SUBST` 的目标文件（`Makefile`）。
   传的是 `X11_CFLAGS="-I/a -I/b"` 时，那对引号**不会被剥掉**，成为 Makefile 里变量值的一部分。
2. **环境变量**：变量未出现在命令行时回落到同名环境变量，值由 autoconf 正常展开，不带多余引号。

走第 1 条时，`make` 展开后交给编译器的是**单个以引号开头的参数**，`-I` 因此整体失效，而编译器**不报错**
——只剩一句下游的"头文件找不到"。`configure` 阶段完全正常，所以按 configure 的退出码判断会得出"参数已生效"的错结论。

## 解决方案

1. **`AC_ARG_VAR` 家族一律走环境变量**注入（conan 侧用构建环境 / `VirtualBuildEnv`，或 `self.run` 前置赋值），
   configure 命令行 ⛔ 再带同名参数。
2. **一手判据是生成的 Makefile，不是 configure 的退出码**：
   ```bash
   grep -n '^X11_CFLAGS' <构建目录>/Makefile      # 值以引号开头即命中本条
   ```
3. 确需在命令行传时，把每个 flag 拆成**不带引号的独立参数**，并同样 `grep -n` 复验；
   ⛔ 用"给整串加引号看起来更规范"的写法 —— 那正是本条的触发形态。

## 与既有条目的区别

| 对比项 | `E075`（`knowledge/doc/E075.md`） | 本条 |
|---|---|---|
| 症状 | `fatal error: *.h: No such file`、`pkg-config --cflags` 返回空 | **同**：`-I` 没生效，只剩头文件找不到 |
| 根因 | 设了 `C_INCLUDE_PATH` 后，pkg-config 把这些路径当**系统头目录**，在 `--cflags` 里**主动过滤掉** `-I` | 参数**有**传给编译器，但因引号被烘进 Makefile 而变形，被**静默忽略** |
| 处方 | 从 shell/环境里**移除** `C_INCLUDE_PATH`/`LIBRARY_PATH`，只留 `PKG_CONFIG_PATH` | 改**传值通道**（命令行 → 环境变量），并 `grep -n` 复验生成的 Makefile |
| 一手先例 | `archives/a/actiona`、`archives/b/barrier`、`archives/b/baka` | 本包第 2 轮 create 的失败与改后通过 |

⇒ **同症状、不同因、不同处方**（按 `手册/03` 的 hit 四条件不成立 ⇒ 升独立条目，⛔ 挂到 E075 名下当"已覆盖"）。

一手检索证据（全树扫，⛔ 只扫 `knowledge/graph/*.kv`）：`grep -rl AC_ARG_VAR knowledge/` = 2 个文件，
全在 `knowledge/drafts/DRAFT-libxp-1.0.4-*`（其机制是 `printproto.pc` 元数据不可满足，同姿势不同因）；
`grep -rlE 'config\.status.*引号|引号.*Makefile|静默忽略' knowledge/graph knowledge/drafts` = 0 命中。

## 验证

```bash
# ① 命中判据：生成的 Makefile 里该变量的值以引号开头
grep -nE '^[A-Z0-9_]+_CFLAGS *:?= *"' <构建目录>/Makefile
# ② 处方生效判据：改为环境变量传值后同一 grep 应无输出，且编译行可解析到依赖 include 目录
grep -n "^X11_CFLAGS" <构建目录>/Makefile
# ③ 本包一手对照：改前 'X11/Xlib.h: No such file'，改后同一编译行通过（notes.md 问题表第 2 行）
```

本包实测：①有输出（触发态）、②无输出（修复态）、③两轮 create 的差异即为本条的复现证据。
适用提醒：`libxpm` 一类依赖已发布 OHOS 二进制时，dockapp 的 XPM 面可整体保留，⛔ 顺手照早期"剔掉 XPM 依赖"的先例改配方（那类补丁的前提已变）。
