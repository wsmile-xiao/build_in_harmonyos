# lang-preflight 将 perl 辅助脚本计入主体 + 漏认生成的 autotools configure → 误判 mixed/env_unsupported

- **草稿 ID**: DRAFT-magicrescue-1.1.10-lang-preflight-perl-aux-autotools-release
- **来源**: magicrescue 1.1.10 HarmonyOS PC 适配（lang-preflight 误判 mixed→env_unsupported，按 R47 D.4 边界规则判主语言 C 后继续适配并全流程通过）
- **分类**: preflight / build-system / language-detection / r47
- **状态**: 本地草稿（路径 B 知识库扩展申请中）

## 问题 / 错误签名

- lang-preflight 输出：`"build_system": "none"`、`"detected_language": "mixed"`、`"error_detail": "任务标记 cpp，实测源码为 mixed（none），无法按 cpp 适配"`、源统计 `c:11, perl:10, bash:1（主体占比 52%）` → 工具自动写终态 `env_unsupported`。
- 该判定与源码实况矛盾：magicrescue 是纯 C 数据恢复 CLI（GitHub 官方语言统计首语言 C 70052 bytes），主体程序由 `src/*.c`（8 个）构建。

## 根因（两类漏判叠加）

1. **源文件统计把辅助脚本计入主体**：`_source_stats` 只对 bash 应用"辅助脚本不算主体"排除（D.4），而 `tools/*.pl`（9 个恢复后处理辅助脚本）、`tests/tests.pl`（测试驱动）被计入 perl 主体占比，使 C 占比从 100% 跌到 52%（11/21），低于 70% 单语言阈值 → mixed。
2. **构建系统漏认 autotools release tarball**：`_manifest_scan` 只认 `configure.ac/Makefile.am/Makefile`/CMakeLists.txt 等；而 autotools release tarball 只带**生成的** `configure`（/bin/sh 脚本）+ `Makefile.in`（ASCII），无 autotools 源文件 → `build_system: none`、无 c/cpp 族 manifest 兜底，判定直接落到源码统计。

## 判定纠正（R47 D.4 边界规则）

- 边界规则明确"**辅助脚本不算主体**"：tools/*.pl、tests/tests.pl 为辅助工具/测试驱动，应排除出主体统计。
- 构建系统证据：`file configure Makefile.in` 确认 autotools 生成产物；`src/` 下 8 个 C 主程序文件。
- c/cpp 兼容族（c↔cpp 不迁移）：主语言判定为 C，与任务语言 cpp 属兼容族 → 继续适配主流程，不终止。

## 验证结果

| 环境 | 结果 |
|------|------|
| 本机 · lang-preflight 复现 | `build_system: none` + `mixed` 复现（工具缺陷证据） |
| 手动核对 | `file configure Makefile.in`（/bin/sh 脚本 + ASCII）、GitHub 语言统计 C 主位、src/*.c 8 文件 |
| 继续适配后 | conan-verify G0-G4 + L2/L4/L5 全绿，鸿蒙专项测试 PASS，finish W3 通过 |

## 处理建议

- 本轮：按边界规则覆盖工具终态继续适配（记录证据，最终以真实结果回报；误判的 env_unsupported 终态在最终上报中如实说明并覆盖）。
- 后续（SKILL 框架层，需单独框架 PR）：①`_source_stats` 对 perl/python/shell 辅助脚本与测试驱动参照 bash 排除语义处理；②`_manifest_scan` 增加"顶层 configure + Makefile.in 组合 → autotools"识别。

## 相关

- 相似条目：DRAFT-exr_image-0.1.0-rc3-lang-preflight-aux-manifest（同为 lang_detect 误判，触发为 tests/ 下 Cargo.toml manifest 扫描敏感）、E049（shebang 硬编码路径可移植性）
- 适用边界/反例：主体确为非 c/cpp（如 python/go 主库）时不得用本规则覆盖；c/cpp 兼容族内可覆盖。