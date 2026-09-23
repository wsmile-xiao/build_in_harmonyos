# DRAFT-pforth-bootstrap-dictionary-sign — pforth 2.0.1 解释器 bootstrap 的 Makefile target 分步签名

> **Contributor**: codex | **Status**: DRAFT | **Updated**: 2026-09-20
> **Severity**: medium | **Category**: ohos / bootstrap / elf-signing / makefile
> **Audience**: OHOS 上「先编译工具 → 运行工具生成数据 → 编译最终产物」的轻量 bootstrap 项目

## Scope

pforth 是 ANSI C 写的 Forth 解释器，构建是两步引导（bootstrap）。与编译器自举（重新编译自身，
如 E325 vlang / DRAFT-avr-gcc gcc）不同，pforth 是「运行解释器内核生成 dictionary 数据文件」。
本文记录其 Makefile target 分步签名模式，以及配套的 RESIZE-FILE ftruncate 补丁。

## 背景与构建链

```
make pfdicapp   → 编译 C 内核得到 pforth（可执行）
签名 pforth      → OHOS 必须，因为下一步要运行它
make pforthapp  → 运行 pforth 生成 pforth.dic + pfdicdat.h，再编译 pforth_standalone
签名 pforth_standalone
make test       → 运行 6 个 Forth 测试脚本（t_corex/t_strings/t_locals/t_alloc/t_floats/t_file）
```

- 上游 Makefile 天然提供 `pfdicapp` / `pforthapp` 两个 target，恰好支持「编译内核 → 签名 →
  生成 dictionary → 编译 standalone」的分步推进。
- OHOS 内核拒绝执行未签名外来 ELF（E077/E135），中间产物 `pforth` 必须在运行前签名，
  不能等 `make` 全部完成或 `package()` 再批量签名。

## 关键适配要点

1. **分步 target 而非 `make all`**：`make all` 会在中途运行未签名的 pforth，OHOS 上直接
   `Permission denied`，且失败点难定位。
2. **中间产物签名顺序**：`make pfdicapp` → `binary-sign-tool sign -selfSign 1` + `chmod a+x`
   → `make pforthapp` → 对 `pforth_standalone` 同样签名 → `make test`。
3. **package 布局**：`bin/pforth` + `bin/pforth.dic`（同目录，保证默认 dictionary 查找）+
   `bin/pforth_standalone`（test_package 用它做消费验证）。
4. **依赖**：无第三方 Conan 依赖，仅链接系统 `libm`（Makefile 的 `-lm`）。
5. **RESIZE-FILE ftruncate 补丁**：`t_file.fth` 收缩测试首跑失败，根因 `tmpfile()` 遇只读
   `/tmp`；POSIX 平台改用 `ftruncate(2)` 修复，详见
   `DRAFT-truncate-via-tmpfile-ohos-ftruncate`。

## 验证结果（真机 shadow CI）

| 项 | 结果 |
|---|---|
| L0 / L1 / L4 / L5 | pass |
| L2（--version/--help 冒烟） | skip（pforth 无标准 --version 参数，Forth 风格 -i/-q/-d，非阻塞） |
| L1e 破坏性负测试 | pass（移走 bin/ 后 test 失败，证明实质依赖被测包） |
| 上游 make test | 346 passed, 0 failed（t_file 补丁后 94/0） |
| test_package | 3/3（`3 4 + . => 7`、`2 3 * . => 6`） |

## 与既有条目的关系

- **E325**（vlang 自举编译器）：同为「阶段产物签名」，但 vlang 是重新编译自身的编译器工具链，
  需固定 bootstrap 源；pforth 是「运行解释器生成 dictionary 数据」的轻量场景，用 Makefile
  target 分步即可，无需额外 bootstrap 源。
- **E077 / E135**：ELF 签名机制与 `.codesign` 覆盖边界（本条目不重复展开）。
- **DRAFT-truncate-via-tmpfile-ohos-ftruncate**：RESIZE-FILE 修复的通用化。

## Source

- Package: `archives/p/pforth/2.0.1`
- 配方: `conanfile.py`（build() 分步签名）、`patches/0001-resize-file-use-ftruncate-on-posix.patch`
- 证据: 真机 shadow CI job `pforth-2.0.1-shadow-20260920-143514`，exit 0
