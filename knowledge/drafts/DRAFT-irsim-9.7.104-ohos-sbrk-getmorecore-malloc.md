# DRAFT-irsim-9.7.104-ohos-sbrk-getmorecore-malloc

> 对应 .kv: DRAFT-irsim-9.7.104-ohos-sbrk-getmorecore-malloc.kv
> 状态: draft（待主编审核）

## 错误特征

```
*** MEMORY WARNING ***
Current data size: 9319814944 (9101382K)
I seem to be short on swap space
Will sleep for 15 seconds and try again
```

## 根因

HarmonyOS 平台上 `sbrk()` 调用返回失败（实测 `sbrk(0)` 正常但 `sbrk(4096)`——
4KB 小探测——即返回 `0xffffffffffffffff`，`RLIMIT_DATA` 无限制；R02 探测输出
`sbrk0=0x58ac1e0000 small_4K=0xffffffffffffffff large_4M=0xffffffffffffffff`）。
sbrk 在本平台任何量级都不可用，并非"大分配才失败"，因此 AC_RUN_IFELSE 特性
检测即便在本机运行也会得到同样失败结论，等价于硬编码平台分支；且 autoconf
判定交叉编译时 AC_RUN_IFELSE 不运行，无法真实判定。基于 sbrk 的自研内存分配器
（irsim `base/mem.c` `GetMoreCore`，SYSV/BSD 分支）在 sbrk 失败后进入
"打印 MEMORY WARNING + sleep 15s 重试"循环（`MAXTRIES=5`），进程长时间卡死，
无法启动仿真。

上游同一代码已为 CYGWIN/APPLE 提供 `malloc(nbytes)` 分支（`#if defined(CYGWIN)
|| defined(__APPLE__)`），OHOS 与其共享"不依赖 sbrk 分配"的特性。

## 方案

将 `GetMoreCore` 的 malloc 分支条件扩展为
`#if defined(CYGWIN) || defined(__APPLE__) || defined(__OHOS__)`，irsim 实测：
MEMORY WARNING 消失、进程可启动、`irsim <prm> <sim>` 冒烟通过（4 nodes, exit 0）。

```c
#if defined(CYGWIN) || defined(__APPLE__) || defined(__OHOS__)
private Pointer GetMoreCore( npages )
  int  npages;
  {
    void  *ret;
    int   nbytes;
    nbytes = npages * DATABYTES + PAGE_SIZE;
    ret = malloc(nbytes);
    return ( (Pointer) ret);
  }
#else
...
```

## 验证

- 修改前：`timeout 20 irsim` → MEMORY WARNING + sleep 重试循环，超时被杀（exit 124/141）
- 修改后：`irsim lib/prm/scmos50_5v.prm lib/test/foo.sim -<cmd>` → exit 0，
  输出 `4 nodes; transistors:`，`d`/`exit` 命令正常
- conan create 干净构建 + test_ohos H4（真实仿真）12/12 通过

## 适用边界

- 任何在 OHOS 上用 sbrk 实现自研内存池/堆分配的 C/C++ 软件（irsim 及同作者
  magic 系工具最可能命中）
- `rpl_malloc`/`AC_FUNC_MALLOC` 误判是另一独立问题（见
  DRAFT-ohos-autotools-rpl-malloc），不适用本方案
- 反例：依赖 sbrk 地址连续性语义的分配器，改用 malloc 前需确认不依赖

## 查重差异

- 引擎查询 "sbrk fails malloc GetMoreCore memory allocator" 命中 E476
  （musl 小尺寸 malloc 对齐问题）——根因不同（对齐 vs sbrk 失败），仅
  match_keywords 部分重叠，方案独立
- DRAFT-ohos-autotools-rpl-malloc：rpl_malloc 符号缺失 vs sbrk 运行时失败，
  不同层面，无重复

## 来源

- 触发事件: irsim/9.7.104 适配 HarmonyOS PC 编译记录（2026-09-16）