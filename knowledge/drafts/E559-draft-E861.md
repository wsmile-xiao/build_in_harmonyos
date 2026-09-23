# E559 — 临时文件模板缓冲区按硬编码 /tmp 路径长度定长计算：长 TMPDIR 被拒绝或截断

> **Status**: DRAFT（pending_editor_review）| **Severity**: 🟡 medium
> **Source**: libmatio/1.5.30 HarmonyOS PC AArch64 适配（feat/libmatio-1.5.30）

## 相关既有条目（同族差异化定位）

与 E002 族（"/tmp 只读"）共享环境背景，但**问题类不同**，非重复条目：

| 既有条目 | 收录状态 | 同族点 | 本条目的增量（差异化） |
|---------|---------|--------|------------------------|
| **E002** | 正式收录 | /tmp 只读、TMPDIR 根因 | E002 解决"脚本/工具遵守 TMPDIR"（set-env-var 即可）；本条目是**库源码即使读了 TMPDIR 也装不下**——缓冲区按 21 字节定长 |
| **E118/E136** | 正式收录 | configure 期 mktemp 失败 | 它们是 autotools configure 阶段；本条目是**库运行期** C 代码路径 |
| **DRAFT-libkml-ohos-tempfile** | 草稿 | 硬编码 /tmp 不读 TMPDIR | libkml 根本不查 TMPDIR；matio 是**查了 TMPDIR 但 snprintf 长度检查拒绝长路径**——修复重点在缓冲区大小而非目录解析 |
| **DRAFT-ohos-otmpfile-tmpdir-shim** | 草稿 | 库不查 TMPDIR、LD_PRELOAD 绕过 | 那是二进制不可改时的 shim 方案；本条目是源码级正确修复（我们控制配方补丁） |

## 错误特征

```text
ctest: 391/8197 failed（readwrite_delete_variables 系列全灭）
Mat_Critical: Cannot create a unique file name   ← mkdtemp("/tmp/XXXXXX") EROFS
# 设 TMPDIR 也无效：snprintf 返回值 > sizeof(buf) → 回退 /tmp → 仍 EROFS
```

## 触发条件

- 构建系统: 任意（本例为 CMake）+ 上游 C 源码自带测试
- 阶段: ctest / test_package / 运行期
- C/C++ 库用 `mkdtemp`/`mkstemp` 生成临时文件模板（"写临时副本再 rename"的原子更新模式，如 matio 的 `Mat_VarDelete`），且：
  - 模板缓冲区大小按硬编码 `"/tmp/XXXXXX"` 短路径计算（matio 1.5.30 为 21 字节）；
  - `snprintf(buf, sizeof(buf), "%s/XXXXXX", dir)` 的返回值检查在长目录下失败 → 静默回退 `/tmp`；
  - 目标环境 TMPDIR 是长路径（CI 工作区、嵌套构建目录）且/或 `/tmp` 只读（OHOS erofs）。

## 根因分析

```c
/* 上游 matio 1.5.30 src/mat.c：21 字节缓冲区 + 硬编码 /tmp */
#define MAT_MKTEMP_DIR  "/tmp/"
#define MAT_MKTEMP_TPL  "XXXXXX"
#define MAT_MKTEMP_FILE "/temp.mat"
#define MAT_MKTEMP_BUF_SIZE \
    (sizeof(MAT_MKTEMP_DIR) + sizeof(MAT_MKTEMP_TPL) + sizeof(MAT_MKTEMP_FILE) - 2)
/* = 6 + 7 + 10 - 2 = 21 字节：任何真实 TMPDIR 路径都装不下 */
```

两层叠加：(1) OHOS `/tmp` 只读 → 硬编码路径直接失败；(2) 即使解析 TMPDIR，21 字节缓冲区对真实路径（本例回归目录 >100 字节）必然触发 `snprintf` 截断保护 → 回退 `/tmp` → 同样失败。

## 解决方案

### 推荐方案

1. **目录解析**：优先 `getenv("TMPDIR")`（去除尾斜杠），回退 `/tmp`——与上游未设 TMPDIR 时行为完全一致；
2. **缓冲区大小**：`PATH_MAX + 模板 + 文件名`（`#ifndef PATH_MAX` 时回退 4096，GNU/Hurd 类平台安全）；同一宏管住所有相关缓冲区（matio 中 `Mat_VarDelete` 的 `path_buf`/`dir_buf` 与 `Mat_mktemp` 的模板共用）;
3. **回归测试**：test_package 用长度**超过旧缓冲区**（>21 字节）的真实可写 TMPDIR，走完整语义链：创建→写入→删除→重读，断言返回值与数据完好（防"只删内存不落盘"假阳性）。

### 禁止做法

- ❌ 禁止 `sizeof("/tmp/")+N` 式定长小缓冲区（长 TMPDIR 必截断）；
- ❌ 禁止硬编码设备/个人绝对路径（`/storage/Users/...`、`/home/x/...`）作回退——必须 TMPDIR→/tmp POSIX 链；
- ❌ 禁止 `|| true` 跳过失败的删除类测试或削减断言换取绿色。

## 验证

```bash
# 修复前：TMPDIR 为超长路径时 ctest -R readwrite_delete_variables → 391/8197 失败
# 修复后：
TMPDIR=$(mktemp -d)/$(python3 -c "print('d'*80)") ctest            # 8197/8197 全过
conan test test_package libmatio/1.5.30 ...                        # 100 checks, 0 failures
```

- 修复前：391/8197 失败（全部 readwrite_delete_variables 链）
- 修复后：`100% tests passed, 0 tests failed out of 8197`（conan create 内 ctest 完整顺序跑）
- test_package：100 checks, 0 failures（含 verify_long_tmpdir_delete 长路径回归）
- ELF64 AArch64 验证 + matdump 实际运行通过

## 关联条目

- 相关: E002（/tmp 只读·环境根因）、E118/E136（configure 期 mktemp）
- 相似草稿: DRAFT-libkml-1.3.0-ohos-tempfile-null-guard、DRAFT-ohos-otmpfile-tmpdir-shim
- 原则: P014
