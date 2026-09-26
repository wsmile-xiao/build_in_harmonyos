# ctags — Universal Ctags

## 软件简介

Universal Ctags（u-ctags）是一个维护中的 ctags 实现，用于为源代码文件中的语言对象生成索引（标签）文件。它是 Exuberant Ctags 的继任者，支持 150+ 种编程语言。

ctags 生成的标签文件可被 Vim、Emacs 等编辑器用于代码导航，支持快速跳转到函数、类、变量等定义位置。

- **主页**: https://ctags.io/
- **源码**: https://github.com/universal-ctags/ctags
- **许可证**: MIT

## 编译信息

| 版本 | 状态 | 编译日期 | 构建系统 |
|------|------|---------|---------|
| 6.2.1.1 | built | 2026-09-26 | autotools |
| 6.2.1 | built | 2026-07-06 | autotools |

## OpenHarmony 适配要点

| 补丁 | 说明 |
|------|------|
| `0001-config.guess.patch` | HarmonyOS 的 `uname -s` 返回 `HarmonyOS` 而非 `Linux`，上游 config.guess 无法猜出 build triple。补丁新增 `*:HarmonyOS:*:*` 分支，映射为 `<machine>-unknown-linux-ohos`（上游 config.sub 已支持 `ohos*`，无需改动） |
| `0002-configure.patch` | HMDFS 上 toybox `mktemp -d` 产生的 0700 目录无法被调用用户写入（且 HMDFS 忽略 chmod、`test -w` 虚报可写）。补丁令 `config.status` 改用 `mkdir` 创建临时目录 |

详细根因与验证见 [`6.2.1/notes.md`](6.2.1/notes.md)。

## 产物

| 文件 | 大小（字节） | 链接方式 | 说明 |
|------|------------|---------|------|
| ctags | 3614656 | 静态 | 主程序，生成标签文件 |
| readtags | 1304512 | 静态 | 标签文件读取/查询工具 |
| optscript | 3614656 | 静态 | 内嵌脚本解释器 |

所有二进制均为静态链接（无 PT_INTERP），适用于 OpenHarmony (aarch64) 平台。

## 上游测试

`make check`（autotools）实际执行，退出码 0：

| 阶段 | 用例数 | 通过 | 失败 | 跳过 |
|------|-------|------|------|------|
| tmain + units | 1574 | 1528 | 0 | 46 |
| tlib | 1 | 1 | 0 | 0 |
| man-test | 22 | 22 | 0 | 0 |
| tutil | 11 | 11 | 0 | 0 |
| **合计** | **1608** | **1562** | **0** | **46** |

跳过项均因可选构建特性未启用（xpath/json/pcre2/sandbox 等），非平台失败。逐项清单见 [`6.2.1/reports/upstream-test-case-list.txt`](6.2.1/reports/upstream-test-case-list.txt)，统计报告见 [`6.2.1/reports/upstream-test-report.md`](6.2.1/reports/upstream-test-report.md)。
