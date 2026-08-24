# DRAFT: calc musl fpos_t 文件位置跟踪兼容性（已修复）

> **草稿状态**: draft | **所属软件**: calc 2.15.1.0 | **阶段**: testing
> **关联正式条目**: 无（当前仅为 draft，未提升为 E 条目）

---

## 问题摘要

calc 在 HarmonyOS musl 环境下的回归测试（`make check -j1`）出现 22 个失败，全部集中在文件位置跟踪相关测试。根因是 musl libc 的 `fpos_t` 是结构体类型（`struct { off_t __pos; mbstate_t __state; }`），而 calc 的 `f_tell`/`f_seek_set` 函数和 `FILEPOS` 类型按整数处理 `fpos_t`，导致 `fgetpos` 返回的 struct 数据被解释为巨大整数。

## 修复方案

已通过最小补丁修复，修复后上游 9998/9998 全部通过：

1. **补丁 0001**：修改 `have_fgetsetpos.c`，将 `typedef fpos_t FILEPOS;` 改为 `typedef off_t FILEPOS;`，使 `FILEPOS` 成为 64 位整数类型（而非 16 字节 struct）
2. **补丁 0002**：修改 `file.h` 中 `f_tell`/`f_seek_set` 宏，从 `fgetpos`/`fsetpos`（操作 `fpos_t` struct）改为 `ftello`/`fseeko`（操作 `off_t` 64 位整数）

补丁路径：`archives/c/calc/2.15.1.0/patches/0001-*.patch` 和 `0002-*.patch`

## 修复前后证据

### Test-First 验证（test_fpos.cal，13 条断言）

| 断言 | 修复前 | 修复后 |
|------|--------|--------|
| fopen w+b | PASS | PASS |
| fputs 写入 | PASS | PASS |
| rewind | PASS | PASS |
| rewind 后 ftell == 0 | **FAIL**（返回巨大乱码 7170310590227061835506233901086） | PASS |
| ftell 不为巨大乱码 | **FAIL** | PASS |
| 读取第一行内容 | **FAIL** | PASS |
| 第一行后 ftell == 27 | **FAIL** | PASS |
| 读取第二行内容 | **FAIL** | PASS |
| 第二行后 ftell == 38 | **FAIL** | PASS |
| fseek 16 | PASS | PASS |
| 偏移 16 处读取 | **FAIL** | PASS |
| fclose | PASS | PASS |
| 清理 test_fpos.dat | PASS | PASS |
| **合计** | **6 PASS / 7 FAIL** | **13 PASS / 0 FAIL** |

### 上游回归测试（make check -j1）

| 指标 | 修复前 | 修复后 |
|------|--------|--------|
| 通过数 | 9976 | 9998 |
| 失败数 | 22 | 0 |
| 通过率 | 99.78% | 100% |

## 影响范围

- **calc 2.15.1.0** 在 HarmonyOS 上的文件位置跟踪功能（`search()`、`ftell()`、`fseek()`、`fgetpos()`/`fsetpos()` 相关操作）
- 文件内容读写功能不受影响
- 非文件 I/O 运算功能（算术、矩阵、数论等）完全正常
- 修复后所有门禁通过：conan create exit 0（test_package 4/4）、conan-verify G1-G4 PASS、W3 本地 CI 通过

## 复用价值

这不是 calc 专属孤例，而是可复用的 musl 文件定位兼容性案例：

1. 任何使用 `fpos_t` 作为整数类型（`long`、`off_t` 等）的 C 语言项目在 musl libc 上都会遇到同样问题
2. glibc 的 `fpos_t` 虽然也是 struct，但 `__pos` 字段布局兼容整数赋值；musl 的 `fpos_t` 布局不同
3. 本案例的修复方法（`FILEPOS → off_t` + `ftello`/`fseeko`）可作为未来 musl 文件定位兼容性问题的查重参考和直接复用方案
4. 新增的通用测试 `test_fpos.cal`（13 断言）可作为其他项目验证文件位置语义的基线

## 查重关键词

- `calc`
- `fpos_t`
- `fseeko`
- `ftello`
- `file-position`
- `musl`
- `HarmonyOS`
- `regress.cal`
- `fgetpos`
- `fsetpos`

## 参考文档

- `knowledge/musl-glibc-full-comparison-iso-posix.md` — 通用 musl 兼容性对比
- `knowledge/musl-glibc-developer-impact.md` — musl 差异对开发者的影响
- R03 适配报告（修复前 22 失败）
- R08 修复报告（修复后全部通过）
- 修复补丁：`archives/c/calc/2.15.1.0/patches/0001-*.patch`, `0002-*.patch`

## 明确声明

当前仅为知识草稿（draft），不是正式知识条目。问题已通过最小补丁修复，测试已验证。正式提升需经过以下流程：

1. 审阅草稿内容的完整性和准确性
2. 分配下一个可用 E 编号（如 `E306`）
3. 重命名并移动到 `knowledge/graph/E306.kv` 和 `knowledge/doc/E306.md`
4. 在 `knowledge/graph/index.tsv` 添加一行