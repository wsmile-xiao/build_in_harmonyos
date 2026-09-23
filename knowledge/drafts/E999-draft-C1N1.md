# E999 — OHOS libc open_memstream：fclose 丢弃未冲刷缓冲并返回 EBADF——close 前必须 fflush

- 触发实例：c-json 1.0.0 适配（任务 #6692，PR 创建后回填），`archives/c/c-json/1.0.0`
- 状态：草稿，拟纳入正式知识库

## 可复现症状与稳定错误签名

c-json 1.0.0 探索构建（OHOS aarch64 原生 meson）上游测试 2 项中 2 项失败：

```text
4/6 c-json:test-basic  FAIL  killed by signal 6 SIGABRT
Assertion failed: string && !strcmp(string, "foo äbc") (../src/test-basic.c: test_basic: 18)
6/6 c-json:test-reader FAIL  exit status 1
  n_array_1_true_without_comma.json ... FAIL（其余 316 个样例以"空输入"假通过）
```

最小复现（直接链接 libcjson-1.a 调用 reader）：

```text
in="foo"    rc=0 out=()      ← 调用成功返回 0，但产物字符串为空
in="\u00e4" rc=0 out=()      ← 与转义解码无关，所有字符串都为空
```

稳定签名：**`open_memstream` 写入成功、`fclose` 返回 EBADF(-9)、缓冲内容为空**——库层面表现为"API 返回成功但字符串为空"的静默数据损坏。

## 根因与最小复现

对 OHOS libc 的 stdio 内存流做行为探针（三个最小程序，全部保留在任务目录）：

| 操作序列 | 结果 |
|----------|------|
| `fputs("hello")` → `fclose` | `fclose=-9 (EBADF)`，`n=0`，`s=`（**数据全部丢失**） |
| `fputs("hello")` → `fflush` | `fflush=0`，`n=5`，`s="hello"`（内容立即正确落盘） |
| `fputs+fflush` → `fputc('!')` → `fflush` → `fclose` | 前 5 字节正确、第 6 字节丢失；`fclose=-9` |
| `setvbuf(_IONBF)` 后写 → `fclose` | `n=1`，`s="x"`（无缓冲层数据不丢） |

**根因**：OHOS libc（musl 变体）的 `open_memstream` 在 `fclose` 路径上先关闭/解绑底层句柄（返回 EBADF）而不执行 stdio 缓冲到内存缓冲的冲刷；只有显式 `fflush`（或无缓冲模式）能让数据落进目标缓冲。这是平台 libc 缺陷，不是应用 bug。

最小复现：任意 OHOS 进程中 `open_memstream` + 写入 + 直接 `fclose`，检查 `strlen` 即可复现（无需 c-json）。

## 已尝试方案（含失败）

1. **怀疑 `\uXXXX` 解码逻辑**（aarch64 char 符号性假设）：用最小复现程序逐输入测试，纯 ASCII 也为空 → 排除解码层。
2. **怀疑 `read_string` 收尾逻辑**（`*stringp` 赋值/cleanup 顺序）：读源码确认 `stream = c_fclose(stream)` 先于 `*stringp = string`，逻辑正确 → 排除。
3. **对 libc 行为做四象限探针**（上表）→ 定位到 `fclose` 丢缓冲；`fflush` 先行则数据完好 → 确认修复点。

## 最终方案与真实验证

**修复**（c-json 补丁 0001/0002，portability、无平台宏）：在 `open_memstream` 流的每个 `fclose`/`c_fclose` 前补 `fflush(stream);`，共 2 处（`src/c-json-reader.c` 的 `read_string`、`src/json-validate.c` 的 `read_file`）。`fflush` 在所有 POSIX 平台语义等价且无害，可回馈上游。

**验证**（补丁前后对比，同一命令 `meson test -C build --print-errorlogs`）：

| 阶段 | test-basic | test-reader |
|------|-----------|-------------|
| 修复前 | SIGABRT（断言失败） | 1/317 判 FAIL（其余空输入假通过） |
| 修复后 | ✅ OK 0.24s | ✅ OK 54.32s，317/317 样例真实判定 |

消费者测试（test_package，-DNDEBUG 显式返回码风格）1/1 通过；`conan-verify` G0-G4 全过（W3 exit_code=0）。

## 适用范围、反例、解除条件和风险

- **适用**：OHOS（及任何表现出相同 libc 行为的平台）上使用 `open_memstream` 的全部代码路径；`fmemopen`/`open_wmemstream` 建议同法探针验证。
- **反例**：标准 glibc/musl 上游平台无需此修复（fflush 幂等，加了也无害）；`fmemopen`（读方向）问题见 E320，需 configure 运行时探测而非本条目的固定修复。
- **解除条件**：OHOS libc 修复 `fclose` 丢缓冲行为后，本补丁仍无害可保留。
- **风险**：无——`fflush` 在无缓冲数据时为 no-op，语义不改变。

## 查重与新增价值

- 引擎最近邻 **E302**（"Gate open_memstream on its close and flush contract, not symbol presence"）已覆盖同一 libc 缺陷的**探测与禁用策略**：符号存在 ≠ 契约可用，建议行为探针验证 write/fclose/缓冲发布，不可探测时证据绑定地 `HAVE_OPEN_MEMSTREAM=OFF` 并回退真实文件流；且 E302 的 forbid 明确反对 pre-flush 工作法（理由：留下未关闭的坏 cookie 流、以跳过掩盖失败契约）。**人工根因核对结论：不合并、创建新条目**——E302 面向 CMake/测试基建的"能力开关"场景，禁用后仍有上游回退路径可用；c-json 的核心 API（read_string）本身以 open_memstream 为唯一实现，**无能力开关也无回退路径**，只能修流。本条目给出库 API 场景的最小修复：flush 前置使数据安全落盘，fclose 照常执行（cookie 清理仍发生，EBADF 返回值忽略），既不泄漏也不跳过测试，正面回应了 E302 forbid 的两条理由；draft-review 引擎判定 create（相似度 0.13，最高分近邻即 E302）。
- **E320**（gnucobol 3.2：`fmemopen` 运行时不可用，AC_RUN_IFELSE 探测 + 临时文件回退）：同属 OHOS stdio 内存流家族的**读方向**探测方案，与本条目（写方向 open_memstream 数据丢失 + 修复）互补，二者可叠加使用。
- 新增价值：①给出可复用的 libc 行为判废探针（四象限表：flush/无缓冲 × close 时序）；②覆盖"调用成功但内容为空"这类**静默数据损坏**的误诊路径（极易误判为库逻辑错误而改错层）；③为 E302 的禁用策略补上"库 API 无回退可禁用时怎么办"的缺口。
