# E635 草稿：已获准的纯 shell CLI 被旧语言预检阻断

## 症状与复现

`xtitle 1.0.4` 的官方上游包只含 `xtitle.sh`、`xtctl.sh`、`Imakefile`、手册及版权文件。旧任务 `lang-preflight` 预期 `cpp` 时报告 `detected_language=other`、`source_stats=无源文件可统计`，自动写 `env_unsupported`；源码并未出现 C/C++ 构建错误。本轮任务已明确允许纯 shell 程序适配。

## 根因

`scripts/ohc/lang_detect.py` 的 `_source_stats` 统计 `.sh` 但从决定主体语言的 `total` 中排除 Bash，并假设 Bash 只作为辅助脚本；纯脚本 CLI 则不成立。`Imakefile` 是可选安装规则，并不意味着存在 C/C++ 构建目标；`other(none)` 不是“无法通过 Conan 发布”的证据。

## 处置与边界

1. 先查任务准入政策、上游源码和原版版本；**仅已批准的脚本包**把语言预检任务类型显式设成 `other` 并记录理由，绝不改 C/C++ 统计或伪造编译。
2. 将原脚本直接复制到 Conan `bin/`，声明 CLI `commands.json`；真实 `test_package` 对包内两条脚本执行 7 项转义序列和版本断言。目标平台无 ELF 编译步骤，x86 上的脚本消费测试不等于 aarch64 真机 GUI 测试；`qemu-aarch64` 不适用于 shell 本体。
3. 未明确允许纯脚本的任务仍走真实语言/能力上报，不得以 `--lang other` 擅自扩大任务范围。

验证：`python3 scripts/ohc-run.py lang-preflight xtitle 1.0.4 --src /root/tmp/builds/xtitle-1.0.4.work --lang other`；`python3 scripts/ohc-run.py conan-verify xtitle 1.0.4`（G2 + 7/7 断言）。

## 去重与建议

`engine` 对综合报错错命中 E352（Lua 模块），对 G1 缺 `build()` 命中 E257（无构建包配方门禁）。现有 `DRAFT-lzav-5.17-langpreflight-headeronly-other` 针对 **C/C++ 单头文件**的 `other` 假阴性，本条针对**真实纯脚本且准入政策已改变**；根因相似，但修复边界不同。请主编审查后择机 promote，若工具已有更精确的 shell 条目请合并而非新增重复条目。
