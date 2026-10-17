# E429 — musl sysroot 下 BSD 风格类型别名（u_char / u_int*_t / caddr_t）不可见

> 类型：知识库草稿（draft） ｜ 关联正式条目：E113（similar_to） ｜ 类别：`platform, compat`
> 来源：dcc-extras 2.3.169（OHOS/HarmonyOS PC，aarch64，clang 15，musl sysroot）

---

## 1. 使用说明（怎么用这条知识）

适用者：把 C/C++ 三方库适配到 OHOS 时，编译期出现 `unknown type name 'u_char' | 'u_int32_t' | 'caddr_t' | 'u_int' | 'u_long'` 的场景。

**三步处置流程**

1. **判定 sysroot 是否已提供这些别名（探针，决定性）**
   ```bash
   # 用真实 sysroot 的编译器跑探针：能打印出 typedef 即“已提供”
   printf '#include <sys/types.h>\n' > probe.c
   $CC -E probe.c | grep -nE 'typedef .*u_char;|typedef .*u_int32_t;'
   # 命中 → 走【方案 A】；无命中 → 走【方案 B】
   ```
   > 关键陷阱：**不要用 `#ifdef u_char` 判断**。`u_char` 是 typedef 不是宏，`#ifdef` 恒为假；
   > 上游 autoconf 探针正是用 `#ifdef u_int*_t` + `grep` 预处理输出，得到"存在"的**假阳性**结论，
   > 与源码实际情况相反（DCC 的 `configure` 就报了 `checking for u_int32_t... yes`，而源码其实编译不过）。

2. **方案 A（首选，探针命中时）**：让真正使用这些类型的**头文件**显式包含 POSIX 头
   ```
   + #include <sys/types.h>     /* u_char / u_int*_t / caddr_t */
   ```
   这是 POSIX 保证存在的头，**无条件添加即可**（无需平台宏、对 glibc/BSD/macOS 等价无害）。

3. **方案 B（探针无命中时）**：sysroot 确实没有这些别名，改用 E113 的 compat 头方案
   （自建 `ohos_compat.h` 定义缺失类型 + 通过 `CFLAGS/CMAKE_C_FLAGS=-include` 注入）。
   ⚠️ 两种方案**不可叠加**：方案 A 命中的 sysroot 上再定义同名 typedef 会与 sysroot 定义冲突。

**验证（必须做）**：修复后全量重编，并让消费者测试**实际引用**这三个类型（编译期即断言），
例如 `u_char c=0x5a; u_int32_t u=0x01020304; caddr_t p=NULL;`。

---

## 2. 适用范围

| 维度 | 覆盖范围 |
|---|---|
| 平台 | OpenHarmony / HarmonyOS PC（`os=OHOS`），sysroot 基于 **musl** 的任意版本 |
| 语言 | C / C++（含 K&R 风格旧代码） |
| 构建系统 | 不限（autotools / cmake / make / meson 均可命中） |
| 代码特征 | 使用了 BSD 遗留别名 `u_char/u_short/u_int/u_long/u_int8_t/u_int16_t/u_int32_t/u_int64_t/caddr_t/quad_t/u_quad_t`，且**未显式**包含 `<sys/types.h>` |
| 反向（不适用） | glibc/Bionic 目标；或源码本就显式包含 `<sys/types.h>`（此时别名可见，问题另有其因） |

**根因（一句话）**：glibc 的 `<sys/socket.h>`/`<netdb.h>`/`<netinet/in.h>` 会**传递**引入 `<sys/types.h>`，
而 musl 不会；且 musl 的这些别名只在 `<sys/types.h>`（受 `_GNU_SOURCE`/`_BSD_SOURCE` 门控）。
以 glibc 为隐含前提的旧代码因此"只在 musl 上"编译失败。

---

## 3. 输入 / 输出定义

**输入**
- `compile_error`：编译器 stderr 片段，须含 `unknown type name '<alias>'` 与出错的头文件:行号
- `sysroot`：目标 sysroot 根（可含 `usr/include/sys/types.h`）
- `cc`：与构建一致的编译器（含 `-I/-D` 上下文，避免探针结论与真实编译不符）
- `usage_site`：首个报错位置（头文件 + 类型名）

**输出**
- `verdict`：`ALIASES_PRESENT_IN_SYSROOT` ｜ `ALIASES_MISSING_IN_SYSROOT`
- `fix`：`add_include_sys_types` ｜ `add_compat_header(inject_cflags)`
- `patch`：最小补丁（优先 1 行、无平台宏）
- `evidence`：探针原始输出（`grep -nE 'typedef .*u_char;'` 的命中行）
- `reverify`：`make -j` + 消费者测试引用三类型的编译结果

**失败判据**：若在 `ALIASES_PRESENT_IN_SYSROOT` 的情况下仍新建 compat 头并定义同名 typedef，
视为**错误输出**（与 sysroot 定义冲突；后续症状为 `typedef redefinition` 或行为不一致）。

---

## 4. 示例（dcc-extras 2.3.169 实录）

**症状**（首个错误，全树 93 个 `.c` 同错）
```
In file included from ../include/dcc_defs.h:19:
../include/dcc_errlog.h:16:8: error: unknown type name 'u_char'; did you mean 'char'?
extern u_char dcc_no_syslog;
       ^~~~~~
```

**判据探针（命中 → 方案 A）**
```bash
$ printf '#include <sys/types.h>\n' > /tmp/t.c && clang -E /tmp/t.c | grep -c 'typedef unsigned char u_char;'
1                      # sysroot 已提供：/…/sysroot/usr/include/sys/types.h:64
$ clang -E /tmp/t.c | grep -n 'u_int8_t;'
60:typedef unsigned char u_int8_t;      # 同理 u_int16/32/64_t 均在此
```
> 反例证据（上游探针的假阳性）：`configure` 报 `checking for u_int32_t... yes`，
> 但源码里 `include/dcc_types.h` 并未包含 `<sys/types.h>` → 全树编译失败。

**最小修复（1 行，无平台宏）**
```diff
 #include <netdb.h>
 #include <netinet/in.h>
+#include <sys/types.h>			/* POSIX: u_char/u_int*_t/caddr_t live here */
 #include <sys/param.h>			/* for FreeBSD */
 #include <sys/socket.h>
```

**验证（重新编译 + 消费者断言）**
```bash
$ make -j8                       # rc=0，20 个 SUBDIR 全绿
$ # 消费者测试（test_package）实际引用三类型，编译通过即断言成立
u_char c=0x5a; u_int32_t u=0x01020304u; caddr_t p=NULL;
→ dcc-extras consumer test OK（DCC_HOMEDIR=/var/dcc, u_char/u_int32_t/caddr_t 可用）
```

---

## 5. 关联与协作

- **similar_to: E113** —— E113 给出"新建 `ohos_compat.h` + `-include` 注入"的通用兜底方案（其
  `error_signature` 与本条完全同族）。本条补充**优先级判据**：musl sysroot 往往**已提供**这些别名，
  此时应优先"补 `#include <sys/types.h>`"而非重复定义；E113 明确"不能把 compat 定义放进 `#if __APPLE__`"
  的教训同样适用于本条（判据必须来自探针，而非平台宏猜测）。
- **prescan**：可在源码预扫描阶段检索 `u_char|u_int[0-9]+_t|caddr_t|u_long` 的出现文件与其 include 列表，
  提前预警"缺 `<sys/types.h>`"。
- 正式入库前建议：主编决定本条是**独立 E 条目**还是**并入 E113 作为补充章节**（预审建议：独立条目 + `similar_to E113`）。
