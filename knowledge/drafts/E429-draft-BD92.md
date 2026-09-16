# E429 — numdiff ssplit() 指针向量槽位未初始化，musl 上向量扫描 SIGSEGV

> **草稿（draft: true）** — contributor_id: `BD92`
> source_event: `archives/n/numdiff/5.9.0`（numdiff 5.9.0 适配 HarmonyOS PC）
> 本文档为 `E429-draft-BD92.kv` 的人类可读版本，二者内容一致。

## 标题
numdiff/ssplit(): 分隔符串以分隔符结尾时指针向量槽位未初始化，musl 上向量扫描 SIGSEGV（malloc → calloc）

## 错误特征
- **trigger_tool**: `runtime | test | numdiff`
- **phase**: `runtime | testing`
- **error_signature**（正则，`|` 分隔）:
  `Segmentation fault.*numdiff` | `numdiff.*-D.*SIGSEGV` |
  `ssplit.*uninitialized.*vector` | `is_char_in_vector.*SIGSEGV` |
  `core dumped.*numdiff`
- 典型症状：`numdiff -D 'a ' a b` 直接段错误，进程以 139（SIGSEGV）退出。

## 触发条件
- 构建系统: 与构建系统无关（C 语言运行期 UB；numdiff 自身为 autotools 项目）
- 阶段: runtime / testing（运行被测二进制时）
- 触发输入：把**以分隔符结尾**的字符串传给 `numdiff -D`，例如 `-D 'a '`、`-D 'x '`，
  或上游官方测试套件 test32 用的 `-D '1:   ##  ###  $  \s  \n '`（末尾含空格）。

## 识别层
- **severity**: 2（🟡）
- **category**: runtime, musl, portability, libc
- **match_keywords**: ssplit, calloc, malloc, uninitialized, SIGSEGV, segmentation fault,
  core dumped, delimiter, -D, musl, numdiff, vector

## 根因分析
`linesplit.c` 的 `ssplit(str, sep)` 统计子串数 `n` 时，若 `str` 以 `sep` 结尾会把 `n` 多计 1。
函数随后 `malloc((n+1)*sizeof(char*))` 并置 `sv[n]=NULL`，但填充循环只写入 `[0, i-1]`（`i < n`），
因此 `sv[i .. n-1]` **保持未初始化**：
- glibc 的 `malloc` 常返回清零内存 → 该 UB 被掩盖（可能恰好 `sv[i]==NULL` 而"看似正常"）；
- musl 的 `malloc` 返回非零内存 → `is_char_in_vector()` / `remove_duplicates_from_string_vector()`
  对垃圾指针执行 `strchr()` / `strcmp()` → SIGSEGV。

## 影响范围
任何在 musl（OHOS/HarmonyOS PC 等）上、使用此类"计数多于实际填充"的指针向量构造的 C 程序。
本例：numdiff 5.9.0 `linesplit.c` 的 `ssplit()`；影响上游官方测试套件 test32 的
`k1vs4` / `k1vs4.5` / `kX4_1vs2` 三个用例（修复前 3 项 SIGSEGV，修复后 0 崩溃）。

## 解决方案

### 推荐方案（rec_priority: 1）
- **rec_approach**: `fix-uninitialized-pointer-vector-malloc-to-calloc`
- **rec_description**: 将 `ssplit()` 中 `malloc((n+1)*sizeof(char*))` 改为
  `calloc(n+1, sizeof(char*))`，使所有槽位初始为 NULL，向量在正确位置终止；
  或等价地在填充循环后补 `sv[i] = NULL;`。
- **rec_command**:
  ```bash
  sed -i 's/malloc ((n+1)\*sizeof(char\*))/calloc ((n+1), sizeof(char*))/' linesplit.c
  ```
- **rec_auto_fix**: false
- **rec_impl**: source-patch

### 回退方案
- **fallback_priority**: 2（暂无备选方案填写）

### 禁止做法
- ❌ **forbid_1_pattern**: `在测试或构建脚本中删除/跳过失败用例以掩盖崩溃|mark.*test.*skip|rm .*test3[0-9]`
  - **原因**: 症状是内存未初始化 UB；跳过测试只掩盖问题，numdiff 对真实合法的 `-D` 参数（以分隔符结尾）仍会崩溃
  - **后果**: 交付二进制在 musl 上对合法输入 SIGSEGV，功能缺陷被隐藏（R34/欺骗检测档）

## 验证
```bash
printf '1  2\n3  4\n' > a
printf '1  2\n3  4\n' > b
numdiff -D 'a ' a b; echo "exit=$?"
# 修复前 exit=139（SIGSEGV）；修复后正常比较
```

## 关联条目
- **doc_file**: `doc/E429.md`（提升为正式条目时生成）
- **principles**: 无
- **关系图**: causes / caused_by / similar_to / conflicts_with / prerequisite_of 均为空

---
*draft: true · contributor_id: BD92 · last_updated: 2026-09-10 · source_event: archives/n/numdiff/5.9.0*
