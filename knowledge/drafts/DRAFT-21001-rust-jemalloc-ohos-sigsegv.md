# DRAFT-21001: Rust jemalloc 分配器在 HarmonyOS 上析构路径 SIGSEGV

## 错误特征

```
signal: 11, SIGSEGV: invalid memory reference
Segmentation fault (core dumped)        # rc=139
process didn't exit successfully: ... (signal: 11, SIGSEGV: invalid memory reference)
```

典型表现：程序**已经打印正确输出**，但在退出路径崩溃（rc=139）。

## 根因

HarmonyOS 上 jemalloc（`tikv-jemallocator` / `jemallocator`）的线程缓存 / TSD
析构路径不可用。可稳定复现的三个场景：

1. 进程正常退出（CLI 主流程返回后）；
2. tokio 多线程运行时析构（`Runtime::drop`）——`#[tokio::main]` 生成的 main 在
   `block_on` 返回后即析构运行时；
3. libtest 回收测试线程（单元/集成测试二进制）。

反例（不触发）：`--version` / `--help` 等由 clap 直接 `std::process::exit` 的路径，
以及 3.1 中把 `std::process::exit` 提到 `block_on` 之前的硬退出写法。

实测排除项：

| 试验 | 结果 |
|---|---|
| 保留 jemalloc | CLI 10/10 rc=139；测试二进制 93/148 SIGSEGV |
| `disable_initial_exec_tls` feature | CLI 崩溃消失，测试二进制仍崩（**不足以修复**） |
| 移除 `#[global_allocator]`（其余不变） | 测试二进制 SIGSEGV 全部消失 |
| 最小 tokio 多线程探针（不用 jemalloc） | rc=0，说明与 tokio 本身无关 |

## 推荐方案

在目标依赖表与 `#[global_allocator]` 的 cfg 中**同步**排除 `target_env = "ohos"`，
OHOS 使用平台分配器（见 `rec_command`）。两处必须一致：只改 cfg 会留下未使用的
依赖，只改依赖表会编译失败。

## 参考实现

`archives/z/zizmor/1.27.0/patches/0001-ohos-use-system-allocator.patch`
（zizmor 1.27.0：修复后 CLI 8/8 rc=0，上游测试 562 passed / 0 failed / 35 ignored）。

---
*Draft 由适配任务生成（2026-10-02，zizmor/1.27.0），待人工审核后 promote。*
