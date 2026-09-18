# ngs

Next Generation Shell (NGS) — a language and shell for the everyday work of a
programmer or a sysadmin.

NGS 是一门面向日常开发与运维任务的脚本语言，也可作为交互式 shell 使用。它把
"外部命令、数据结构、并发与异常" 放在同一层抽象上：外部命令的结果是普通的
Process 对象，字符串插值可直接嵌入命令，正则匹配返回带捕获的结构化 MatchResult。

- Homepage: https://ngs-lang.org/
- Upstream: https://github.com/ngs-lang/ngs
- License: Apache-2.0
- Category: lang

## 适配版本

| 版本 | 状态 | 说明 |
|---|---|---|
| [0.2.17](0.2.17/) | built | 上游 762 条 TEST 断言中 754 条实际执行全部通过，8 条因宿主/依赖能力缺口显式跳过 |

## 运行提示

- `ngs` 动态依赖 `libjson-c.so.5`，由 Conan 管理依赖链且不写 RPATH，
  需通过 `conan run` 或 source `conanrun.sh` 启动，裸跑会 `rc=127`。
- 包导出 `NGS_PATH=<pkg>/lib/ngs`，缺失时 `autoload` 模块不会惰性加载。
- 上游 0.2.17 的交互式 CLI 尚未实现，脚本入口使用 `ngs FILE.ngs` 或 `ngs -e EXPR`。
