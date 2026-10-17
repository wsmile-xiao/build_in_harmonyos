# libcester 0.4 — OHOS musl FILE 不透明：header-only 库按值 FILE 字段需 C99 编译模式

> 草稿（DRAFT，路径 B 候选）— 随 libcester 0.4 归档 PR 交付，经审核后可 promote 为正式条目。

## 问题

OHOS musl libc 下编译 header-only C 测试框架（libcester 0.4）失败：

```
include/exotic/cester.h:277:10: error: field has incomplete type 'FILE' (aka 'struct _IO_FILE')
    FILE original_stream;
         ^
.../bits/alltypes.h:328:16: note: forward declaration of 'struct _IO_FILE'
typedef struct _IO_FILE FILE;
```

## 根因

OHOS musl 的 `bits/alltypes.h` 仅在 `__STDC_VERSION__ < 201112L`（C99 及以下）时提供
`struct _IO_FILE { char __x; };` 占位定义。clang 默认 gnu17 下 FILE 为不透明前向声明类型，
任何按值 FILE 字段（`FILE original_stream;`）或按值复制（`*stream = *handle;`）均不可编译。
glibc 的 FILE 是完整结构，因此该问题在 Linux glibc 上不出现，属 musl 系平台（OHOS）特有。

## 方案

编译时强制 C99（与上游 test/CMakeLists.txt 的 `-ansi` 同语义）：

```cmake
set(CMAKE_C_STANDARD 99)
set(CMAKE_C_STANDARD_REQUIRED ON)
```

或命令行 `clang -std=c99 ...`。C99 下 OHOS musl 提供 FILE 占位定义 → 按值字段可编译。
无需源码补丁、无需平台宏（优于 E020 的 source-patch 方案）。

## 验证

- conan create（OHOS aarch64 profile）全流程通过，test_package 消费者 4/4 + 鸿蒙专项 4/4。
- 57 个上游测试全部编译成功（-std=c99），53 文件级通过。

## 适用边界

- 仅影响头文件含 FILE 按值字段/流捕获按值复制的库（header-only 测试框架、mocking/stream-capture 型库）。
- 仅 `FILE*` 指针用法的库不受影响。
- 流捕获功能（CESTER_CAPTURE_STDOUT/STDERR）依赖 FILE 真实结构内容，musl 占位类型无法回读 →
  相关用例如实计失败并列入台账（计入上游分母不计通过），不得伪造通过。

## 查重差异

- similar_to: **E020**（musl FILE 不透明，同族不同症状——E020 针对访问内部字段 _IO_*，本条目针对按值存储 + C99 编译模式 workaround）。
- 七轴：exact_duplicate=否；causal_duplicate=部分；trigger_overlap=部分（`incomplete type 'FILE'` 与 E020 的 `incomplete definition.*_IO_FILE` 有正则重叠但主签名不同）；solution_overlap=低（构建配置 vs 源码补丁）；combination_novelty=是（`__STDC_VERSION__ < 201112L` ↔ FILE 占位定义机制 + C99 workaround 未覆盖）；boundary_novelty=是；test_migration_novelty=不适用。

## 反例

- 纯 glibc 目标平台不会触发；
- 仅使用 `FILE*` 指针、不按值复制 FILE 的库（绝大多数正常 C 库）无需任何改动。
