# DRAFT-ifile-1.3.9-extern-inline

## 一句规则

老 glibc 派生 `argp`（含 argp-standalone 与各包内嵌副本）把**函数定义**写在头文件里并用
`extern inline` 修饰（`argp/argp.h` 的 `ARGP_EI`、`argp-fmtstream.h` 的 `ARGP_FS_EI`），
这套写法只在 **GNU89 内联语义** 下成立；clang 默认已是 C99/C17 语义，`extern inline`
在 GNU11 里的含义是"本 TU 另外发一份强外部定义"，于是**每个包含该头的编译单元**都产出
`argp_usage`/`_option_is_short`/`_option_is_end`/`argp_fmtstream_*` 的强符号，链接期报
`ld.lld: error: duplicate symbol`。正解是给编译标志加 **`-fgnu89-inline`**（一个标志、零源码改动），
而不是 `-fcommon`——后者只治"头中定义的**全局变量**"，对函数无效。

## 背景与可复现症状

包：`ifile 1.3.9`（MH/exmh 朴素贝叶斯邮件分类器，C，autoconf 2.59，内嵌 `argp/` 子工程）。
稳定错误签名（双臂对照，见下）：

```text
ld.lld: error: duplicate symbol: argp_usage
ld.lld: error: duplicate symbol: _option_is_short
ld.lld: error: duplicate symbol: _option_is_end
ld.lld: error: duplicate symbol: argp_fmtstream_write
... 合计 20 条，全部是函数符号，分布在 argp-parse.c / argp-help.c 的真实定义与每个根目录 .o 之间
```

触发条件：任何 `-O` 级别（`-O2`/`-O3` 会定义 `__OPTIMIZE__`，头里的定义块才生效）。
**`-O0` 时该块被条件编译跳过、症状消失**，极易被误判成"优化等级引入的 bug"。

## 根因（机理链）

1. `argp/argp.h` 在 `#ifdef __OPTIMIZE__` 下：
   ```c
   #ifndef ARGP_EI
   # define ARGP_EI extern inline
   #endif
   ARGP_EI void
   __argp_usage (__const struct argp_state *__state) { __argp_state_help (...); }
   ARGP_EI int __option_is_short (...) {...}
   ARGP_EI int __option_is_end (...) {...}
   ```
   且 `#if !_LIBC` 时 `#define __argp_usage argp_usage`、`#define __option_is_short _option_is_short`。
2. `argp-fmtstream.h` 同族：`#define ARGP_FS_EI extern inline` + 8 个 `argp_fmtstream_*` 定义。
3. **上游自己依赖 GNU89 语义**：`argp/argp-fs-xinl.c` 先 `#define ARGP_FS_EI`（置空）再包含该头，
   从而"恰好一个 TU"发出外部可见的实体；`argp-xinl.c` 同构。这正是 GNU89 `extern inline` 的用法
   （inline 定义 + 单独的实体生成点）。
4. clang 15 默认 `-std=gnu17`，内联语义按 C99/C17 解释：`extern inline` ⇒ 本 TU **发出强定义**。
   于是 `libifile.a` 的 13 个成员各带一份 `argp_usage`（`llvm-nm --defined-only libifile.a | grep -c "T argp_usage"` 实测 13），与 `libargp.a` 里 `argp-parse.c` 的
   真实定义冲突 ⇒ `duplicate symbol`。

## 方案空间

* **rec（首选）**：`-fgnu89-inline`。恢复 GNU89 内联语义，`extern inline` 不再发独立副本，
  符号仍由上游指定的 xinl/parse 翻译单元提供。零源码补丁。
  conan 写法 `tc.extra_cflags.append("-fgnu89-inline")`；等价手工命令 `make CFLAGS="-O2 -fgnu89-inline"`。
* **fallback**：覆盖头文件自带的守卫宏——`-DARGP_EI=static inline -DARGP_FS_EI=static inline`。
  诚实权衡：只治 argp 这一族头，不治同族写法的其它头文件；把 inline 变 static 会留下
  "未使用静态函数"警告；需要为每个受影响子工程分别传。
* **禁止 1**：`-fcommon`。它是 `DRAFT-clang-fno-common-header-globals` 那条（头中定义的**全局变量**、
  clang 默认 `-fno-common`）的正解/退路，对本条**经第三臂实证无效**——同源码同工具链只把 CFLAGS 换成 `-O2 -fcommon`，duplicate symbol 计数仍为 20、产物仍不生成（见下表 C 臂）。
* **禁止 2**：手删头中定义或把定义直接改 `static` 而不动声明点——会把 `duplicate symbol`
  变成 `undefined symbol`，并把改动面扩大到源码补丁。

## 真机验证（双臂对照，唯一变量是内联语义）

设备：HarmonyOS PC（OHOS aarch64），`aarch64-unknown-linux-ohos-clang`（clang-15）+ `ld.lld`。
日志：`~/tmp/uc2/hw-7/logs/gnu89-A.log`、`gnu89-B.log`。

| 臂 | CFLAGS | duplicate symbol | `llvm-nm --defined-only opts.o` 中 `T argp_usage` | `libifile.a` 中 | 链接产物 |
|---|---|---|---|---|---|
| A（基线） | `-O2` | **20** | 1 | 13 | 无 `ifile` |
| C（反证 `-fcommon` 非解） | `-O2 -fcommon` | **20** | 1 | 13 | 无 `ifile`（与 A 臂逐字同计数） |
| B（修法） | `-O2 -fgnu89-inline` | **0** | 0 | 0（实体仅由 `argp/libargp.a` 提供） | `ifile` 125376 B，`ifile --version` → `ifile 1.3.9` |

后续 `conan create` 全链路（含上游 8 条 `test.sh` 断言与消费者行为测试）在臂 B 语义下通过。

## 适用边界

* **适用**：内嵌 glibc 时代 `argp`/`getopt`/`argp-fmtstream` 头，或用"头中 `extern inline` 给定义 +
  单 TU 置空宏重生成实体"这套 GNU89 惯用法的 C 包；报错**成组出现且全是函数符号**；`-fcommon` 无效。
  候选画像：任何 bundle 了 `argp-*` 的老 CLI（`argp-standalone` 系、glibc 分叉工具）。
* **反例（不要套用）**：①重复符号是**变量**（`duplicate symbol: progname` 这类）→ 走
  `DRAFT-clang-fno-common-header-globals`；②头里写的是 C99 合规的 `static inline` → 不会撞名，
  加 `-fgnu89-inline` 无意义；③C++ 模板/`inline` 函数 ODR 问题 → 另一族（参见 graaf 草稿）。
* **解除条件**：若上游把 `ARGP_EI` 改成 `static inline`（或改用系统 argp），本条对该包不再适用。
* **风险**：`-fgnu89-inline` 是 GNU 扩展开关，clang 与 gcc 语义一致；若同包内混用 MSVC 风格构建
  则该标志不可用。

## 关系字段

* `similar_to`：`DRAFT-clang-fno-common-header-globals`（`error_signature` 同为 duplicate symbol，
  但根因是变量暂定定义、解法是 extern 化或 `-fcommon`）；`E169`（`argp.h` 缺失，另一族症状）。
* `caused_by`：无。
* `conflicts_with`：无。与 `-fcommon` 条目是**互补**——同一症状措辞、两条不同机理，按
  "重复的是函数还是变量"分流。

## 验收口径（跨库可复用）

先用 `llvm-nm --defined-only <某 TU>.o | grep ' T <符号>'` 判断重复符号是否由**每个编译单元**发出，
再看该符号在头文件里的修饰是不是 `extern inline`（而非 `static inline` 或裸定义）。
两臂对照必须只改内联语义开关一个变量；产物字节数与 `nm` 计数一起给出，避免只看"链接成功"。
