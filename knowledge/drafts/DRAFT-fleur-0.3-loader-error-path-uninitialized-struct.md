# DRAFT-fleur-0.3-loader-error-path-uninitialized-struct：C 加载器错误路径返回未初始化结构体，消费者 free(垃圾指针) 崩溃

> Contributor: pc4-45 | Status: Draft | Updated: 2026-09-26
> Source: fleur 0.3 适配（HarmonyOS PC aarch64，上游测试 suite_2）
> 对应：`knowledge/drafts/DRAFT-fleur-0.3-loader-error-path-uninitialized-struct.kv`
> 关联：`knowledge/graph/E249.kv`（部分覆盖，见查重）

## 现象

上游测试读取**故意损坏**的 Bloom Filter 文件后调用清理函数，进程崩溃：

```console
[ERROR] Incoherent header.
Signal 5 (core dumped)
```

完整日志：上游套件 2 中 `test_reading_full` 对 `hang2.bin`（头文件 p>1）调用
`fleur_bloom_filter_from_file` 得到错误态 filter 后 `fleur_destroy_filter(&bf1)`，
`free` 命中未初始化指针。普通消费者读坏文件同样会崩溃，不只影响测试。

## 根因

`fleur_bloom_filter_from_file` 的**错误路径**（文件头校验失败 / fread 失败 /
seek 失败）只设置了 `bf.error = 1` 就 `return bf;`，而 `bf.v`、`bf.Data`、`bf.M`、
`bf.datasize` 都是**栈上垃圾值**：

```c
struct BloomFilter fleur_bloom_filter_from_file(FILE* f){
    BloomFilter bf;                 // ← 未初始化
    ...
    if (fleur_check_header(&h) != 1){
        fprintf(stderr, "[ERROR] Incoherent header.\n");
        bf.error = 1;               // ← 只设 error
        return bf;                  // ← v/Data/M 是垃圾
    }
```

调用方 `fleur_destroy_filter(&bf1)` → `free(bf1.v)` → 垃圾指针 → SIGTRAP/SIGSEGV。
API 契约要求"加载后无论成败都应销毁"，因此错误态对象必然走到 destroy。

> 与 E249（未初始化所有权标志导致清理函数释放调用者栈对象）同属"未初始化字段→
> 清理函数 free 崩溃"族，但本候选的触发形态是**加载器错误路径早退 + 消费者对
> 错误态对象仍调 destroy**，修复位置在**入口整体零初始化**；E249 是借用对象
> 所有权标志未初始化、释放调用者栈对象，主方案是显式设置 shared/borrowed 标志。

## 方案（按优先级）

### 1. 入口整体零初始化（推荐，+1/-1 行）

```c
BloomFilter bf = {0};   // 错误路径返回时 v=NULL/Data=NULL，free(NULL) 安全
```

不改 API、不改测试、不留空分支；对任何"加载器 + destroy"形态的 C 库通用。
验证：修复后上游套件 8/8 通过，test_ohos T5 与消费者用例均通过。

### 2. 逐错误分支显式置 NULL（次选）

每个 `bf.error = 1; return bf;` 前补 `bf.v = NULL; bf.Data = NULL;`——更局部但
易漏分支，新加错误路径时容易再次漏掉。

## 判别步骤

1. 定位 from_file/load/parse 类加载函数；
2. 确认错误路径 `return` 前只设了 error 字段；
3. grep 调用方是否对错误态对象调 destroy/close/free；
4. 修库源码（不改测试）→ 重建 → 用坏输入用例复验。

## 适用边界 / 反例

- ✅ 适用：C 库从文件/流加载结构体 + 校验失败早退 + destroy 契约。
- ❌ 不适用：无 destroy/清理函数、或错误路径已完整初始化所有字段的库；
  C++ RAII 类对象（默认构造已初始化，不受影响）。
- 平台：非 OHOS 专有——glibc 上同为未定义行为（信号可能为 SIGSEGV），
  HarmonyOS（musl）实测为 Signal 5。
