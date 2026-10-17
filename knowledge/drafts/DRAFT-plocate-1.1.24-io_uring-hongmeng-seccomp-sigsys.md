# plocate 1.1.24 — HongMeng seccomp 分 syscall 封锁 io_uring：setup 放行、register 即 SIGSYS（draft）

**Category**: ohos | kernel | io-uring | security | portability · **Severity**: 2 · **Tool**: meson|cc|liburing|seccomp

## 症状

带 io_uring 可选路径的包在 OHOS PC 上构建、签名、`--version` 全绿，
真实运行时查询进程被击杀，构建期完全无感：

```
Signal 31 (core dumped)
rc=159
```

plocate 实例：`with_uring=True` 变体进入 `setup_uring() →
io_uring_get_probe_ring() → io_uring_register()` 后，fork 出的查询子进程
立即收到 SIGSYS；`--version` 等不触碰 ring 的路径完全正常。

## 根因（分层实测，HongMeng Kernel 1.12.0 / HarmonyOS PC aarch64）

OHOS app 域 seccomp 对 io_uring 是**分 syscall 部分放行**，
不是"内核支持/不支持"二值：

| 层级 | 探针 | 结果 |
|---|---|---|
| `io_uring_setup(4)` | 裸 syscall | ✅ fd=3 |
| `io_uring_register(IORING_REGISTER_PROBE)` | 裸 syscall | ❌ SIGSYS 立即击杀（SECCOMP_RET_KILL，**不可捕获**） |
| `io_uring_queue_init(4)` | 直链 liburing/2.15 | ❌ 同点位死（queue_init 内部注册 PROBE） |

结论：**"setup 能打开"判 uring 可用 = 假阳性**。一切走 liburing 常规初始化的库
在 OHOS app 域必崩。

## 对策

1. **打包期默认降级**：对 `meson dependency('liburing', required:false)` 类
   可选路径，OHOS 默认取非 uring 档（plocate 配方 `with_uring=False`），
   保留 option 供放行内核；不得凭 setup 成功开真值。
2. **探针打到语义终点**：能力探测必须驱动 `io_uring_register`（或一次
   submit/enter 往返），入口级成功不作数。
3. **降级路必须验正确性**：跑到"建库→查询→比对断言"级别，否则 SIGSYS
   之前的一切绿灯都是假通过（plocate 降级路消费者 10/10 实证）。
4. 反例（勿做）：装 SIGSYS handler 救不了（KILL 不可捕获）；把
   `queue_init` 当可返回错误处理也救不了（进程已死）。

## 验证

plocate 1.1.24（2026-09-24，clang 15.0.4 + musl）：

- 裸两档探针复现上表（寄存器语义见 `.kv` 的 rec_command）；
- `with_uring=True`：conan create 通过、查询子进程 SIGSYS rc=159；
- `with_uring=False`：消费者测试 10/10（version/建库/两文件精确匹配/
  -i/-c/-b/-r/-l/空匹配/regex 全量）。

## 适用边界

适用于所有含 io_uring 可选加速路径的包（liburing 消费者）与自研 uring
探测逻辑；非 app 域进程策略可能不同，须按本口径分层重测。

## 与既有条目的分界（查重结论）

| 条目 | 机制 | 与本条差异 |
|---|---|---|
| E051 | 未实现 syscall → SIGSYS（部分不可捕获） | io_uring_setup **已实现且放行**，不是整调用缺失 |
| E246 | seccomp 拦截整只 syscall（adjtimex 等） | 本条是**同一子系统内拆分**：setup 放行、register 击杀 |
| E024/raul | AF_UNIX bind → EPERM（返回值可判） | 本条不可判——进程已被杀，探测语义完全不同 |

新增价值：①"setup 成功 ≠ uring 可用"的假阳性陷阱与分层探针方法；
②liburing 常规初始化在 OHOS 必死的库级结论；③配方默认降级档 +
正确性级验证的处置规程。
