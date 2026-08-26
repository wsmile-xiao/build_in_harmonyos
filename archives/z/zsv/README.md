# zsv

极速流式 CSV 解析器（liquidaty/zsv），HarmonyOS PC 适配归档。

- 上游：https://github.com/liquidaty/zsv
- 许可证：MIT
- 构建：自定义 configure + Makefile（非 CMake）
- 能力：CSV 命令行工具集（`zsv count/select/2tsv/2json/sql/compare` 等）+ C 库 `libzsv.a` / `libzsvutil.a`，
  内置 pcre2 / jq / sqlite3 / utf8proc（builtin，非外部依赖）

## 版本

| 版本 | 状态 | 日期 | 说明 |
|------|------|------|------|
| 1.4.3 | built | 2026-08-15 | OHOS aarch64，NEON 启用，上游测试 28/32 通过 |

## 适配要点

- config.guess HarmonyOS 分支 + umask 077→022（嵌套 pcre2/jq tarball 补丁）
- /tmp 只读 → 临时文件用工作区 tmp
- test-quotebuff-select 在 OHOS 挂起、test-parallel-3+ 上游路径假设 → unrunnable（如实记录）
