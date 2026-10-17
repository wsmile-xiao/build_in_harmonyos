# DRAFT-heatshrink-0.4.1-make-cflags-commandline-override — GNU make 命令行 CFLAGS 追加会静默清空上游 Makefile 的 CFLAGS

**路径**: B（知识库扩展）
**来源任务**: heatshrink 0.4.1 首次适配（feat/heatshrink-0.4.1）
**触发事件**: conan create 内上游 greatest 测试 `decoder_sink_should_reject_null_input_pointer` 段错误（Signal 11），同源码设备原生构建却 13882 全过

## 问题

raw-make 适配需要在构建时追加编译 flags（如 `-fPIC`、宏定义）。直觉写法是
`make CFLAGS+=-fPIC`。在 heatshrink 0.4.1 上，这使 conan create 内的
`test_heatshrink_dynamic` 在 decoding 套件第 6 用例稳定段错误，而去掉该追加后
12282 用例全过——崩溃与"是否追加 flags"相关，且崩溃点与 flag 内容看起来无关。

## 根因

GNU make 变量优先级规则：**命令行定义的变量优先于 Makefile 内一切普通赋值，
且 Makefile 内对该变量的 `+=` 追加同样被忽略**（除非 makefile 使用 `override`）。

上游 heatshrink Makefile:

```make
CFLAGS += -std=c99 -g ${WARN} ${OPTIMIZE}   # OPTIMIZE = -O3
```

配方执行 `make CC=clang AR=ar CFLAGS+=-fPIC all` 后，编译行只剩
`clang -c -o heatshrink_decoder.od heatshrink_decoder.c -fPIC -DHEATSHRINK_DYNAMIC_ALLOC=1`
——上游 `-std=c99 -g -Wall -O3` 全部静默丢失，库实际以 **-O0** 构建。

-O0 显形了上游潜在 UB：`heatshrink_decoder_free` 不 NULL-safe，先解引用
`hsd->window_sz2` 再 free：

```c
void heatshrink_decoder_free(heatshrink_decoder *hsd) {
    size_t buffers_sz = (1 << hsd->window_sz2) + hsd->input_buffer_size;  /* NULL 解引用 */
    ...
}
```

而测试 `decoder_sink_should_reject_null_input_pointer` 以
`alloc(256, window=4, lookahead=4)`（参数非法返回 NULL）→ `free(NULL)`。
-O3 下该解引用是死代码（结果只喂给未使用的 sz），clang 化简为对 libc `free`
的尾调用（`llvm-objdump` 仅一条 `b free` 重定位），`free(NULL)` 合法；
-O0 下死代码保留真实 load（`ldrb w9, [x8, #13]`），解引用空指针 → SIGSEGV。

## 诊断链（可复用）

1. 同源码两个构建一个过/一个崩 → 先 diff 实际编译命令行（conan create 日志的
   `RUN:` 行），再对比 flags 而不是猜平台问题；
2. A/B 二分：逐个增删 flags 定位触发变量（本例：`CFLAGS+=-fPIC` 在场即崩）；
3. 反汇编对比崩溃函数（`llvm-objdump -d`）：`b <reloc>`（尾调用，UB 被消除）
   vs 真实 load 指令（UB 显形），可直接证明"优化级别依赖的段错误"；
4. 最小 C 程序复现崩溃调用序列，排除测试框架因素；
5. greatest 框架用 `-v`（逐用例 PASS 行）与 `-t <name>`（单测隔离）定位崩溃用例。

## 方案（正确姿势）

- **默认不追加**：raw-make 包应原样使用上游 CFLAGS（与设备原生验证口径一致）；
- 确需追加时用**环境变量**：Makefile 的 `CFLAGS +=` 对环境变量是"追加"语义
  （env 基值在前，上游 flags 在后），即 `CFLAGS="-fPIC" make CC=... all`；
- 或打补丁给上游 Makefile 引入专用追加变量（如 `EXTRA_CFLAGS`）——侵入上游，
  仅在前两者不可行时使用；
- 禁止把"上游测试在 -O0 崩溃"当成上游缺陷去改测试或空实现绕过：-O3 是上游
  发布口径，潜在 UB 属上游 bug，可另行上报但不得阻塞本口径适配。

## 验证

- heatshrink 0.4.1（设备 OHOS aarch64, clang 15.0.4）：
  - `make CC=clang AR=ar all -j1`（无 CFLAGS 覆盖）：上游测试 1600 + 12282 全过；
  - 同命令加 `CFLAGS+=-fPIC`：decoding 第 6 用例稳定段错误（5 次复现）；
  - 反汇编：-O3 `heatshrink_decoder_free` = 单条尾调用；-O0 = 含 `ldrb [x8,#13]` 空指针 load；
- 修复后 conan create 全链路 PASS（含 build() 内两个上游套件 + test_package 9/9）。

## 推广价值

适用于**一切 raw-make / 递归 make 的包适配**（bzip2、zlib 类）：任何
`make VAR+=...` 追加编译参数的配方都可能静默丢弃上游 flags。后果不只是优化
丢失——UB 在 -O0 显形会造成"与优化级别相关的段错误"这类高迷惑性失败。
同类场景：追加 `-fPIC`、宏开关（`-DUSE_X=0`）、诊断 flags 时。
