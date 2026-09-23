# roll

`roll` 是一个**命令行骰子/随机数模拟工具**：用一套直观的骰子表达式语言描述要掷的骰子，程序求值并打印结果。上游作者 Matteo Corti（瑞士 ETH 图书馆），GPL-2.0-or-later，语法与语义见 `man roll`（本包随附 `share/man/man1/roll.1`）。

上游 [github.com/matteocorti/roll](https://github.com/matteocorti/roll)。

## 功能概述

骰子表达式语言（实测口径，来自 `roll --help` 与 man 页）：

- 基本骰子：`MdN`（M 颗 N 面骰，如 `3d6` = 三颗 d6 求和）、`1d%`（百分骰，概率均匀的 1–100）、`dF`（Fudge 骰：-1/0/+1）等
- 算术：`+`、`-`、`*`、`/`（向上取整）、`x`/`*` 简写，支持括号
- 保留/丢弃：`4d6h3`（保留最高 3）、`4d6l3`（保留最低 3）、`4d6HX`（丢弃最高）、`4d6LX`（丢弃最低）
- 条件筛选：`d6>3`、`>=`、`<`、`<=`、`!=`（重掷到满足条件为止；不可能的条件会被拒绝）
- 组合：逗号分隔多表达式；`{e1,e2,...}` 与 `N{...}` 重复组
- 输出开关：`-s` 系列求和、`-p` 只保留正数、`-v` 逐骰轨迹、`--test` 确定性模式（每颗骰子恒为 3，测试用）、`--version`、`--help`
- 溢出/除零/非法筛选等错误路径有明确诊断（`Overflow`、`Division by zero`、`Impossible dice filter`），退出码 1

## 依赖关系

- 编译依赖：无（W0 实测：零第三方依赖，仅系统 libc/libm）
- 运行依赖：无
- Conan 依赖：无（配方未声明 `requirements()`）

## OHOS 适配要点

- **1 个平台兼容补丁（`patches/0001-configure.patch`）**：dist 归档自带的 `configure`/`config.status` 用 `umask 077 && mktemp -d "./confXXXXXX"`（回退 `umask 077 && mkdir`）创建临时目录；HMDFS 强制 setgid 并重映射属主 UID，得到的 `drwx--S---` 目录连属主也不可写，`config.status` 以 `./confXXXXXX/subs1.awk: Permission denied` / `could not setup config files machinery` 失败（configure 自身能过，失败发生在 configure 收尾自动执行的 config.status 里）。补丁仅去掉该处的 `umask 077`（单处两行，无平台宏；回退 `mkdir` 同步补 `2>/dev/null`，与 `mktemp` 分支一致），随后 configure/make/make check 全绿；本仓库 948 个 autotools 归档采用同一解法（知识 E011/E114）
- **构建可复现**：`autotools.make(args=["-j1"])`（与上游 `AUTOMAKE_OPTIONS = serial-tests` 一致，也让测试日志可复现）；编译器/标志全部来自 Conan toolchain（R33 无裸 `${CC}`）；`d66`/生成的 `roll.1` 等构建产物不进入补丁
- **上游测试完整保留并在 build() 中强校验**：`make check`（3 个 TAP 脚本 / 15 条确定性断言）在 `timeout -k 5 600` 下执行，要求退出码 0、automake 总结行 `All 3 tests passed`、且 15 条 `Testing '` 断言行一条不少，否则中止构建（R9/R51：不跳过、不伪造通过）；未修改任何上游用例
- 产物为可执行命令：软件级 `commands.json` 按 R38 声明；`package()` 走上游 `make install`（归档自带 install-sh，OHOS/toybox 下实测可用），另复制 `COPYING` 到 `licenses/`

## 参考资料

- 上游项目与发布资产：<https://github.com/matteocorti/roll>（v2.7.0 release asset `roll-2.7.0.tar.gz`，sha256 与 GitHub release API 的资产 digest 一致）
- 上游手册页：`roll.1.in`（本包以 `share/man/man1/roll.1` 交付）

## 版本

- `2.7.0` — 适配 HarmonyOS PC（aarch64-unknown-linux-ohos / armv8）；1 个平台兼容补丁（HMDFS 临时目录权限），上游 15/15 断言通过、test_package 21/21 通过；见 [2.7.0/notes.md](2.7.0/notes.md)

## 产物

| 路径 | 说明 |
|------|------|
| `bin/roll` | 骰子表达式求值器（arm64 ELF） |
| `share/man/man1/roll.1` | 上游 man 手册 |
| `share/bash-completion/completions/roll` | 上游 bash 补全脚本 |
| `licenses/COPYING` | GPL-2.0 全文 |
