# Samba waf 包的 direct-cc 绕行：谁来决定"编哪些文件"和"那个常量是几"

> Draft: DRAFT-TEVENT-0171-WAF-BYPASS-DIRECT-CC-EPOLL-BACKEND
> Stem: `tevent-0.17.1-waf-bypass-direct-cc-epoll-backend` — pairs with the same-stem `.kv`

## 基本信息

- **ID**: DRAFT-TEVENT-0171-WAF-BYPASS-DIRECT-CC-EPOLL-BACKEND
- **严重度**: 2
- **类别**: build-system|waf|portability|ohos-platform
- **触发工具**: conan|clang|configure|make
- **阶段**: configuration|compilation|testing

## 错误特征

这类问题**没有报错**，这正是它的特征：

- 编译全绿、链接全绿、上游单测全过，但 `tevent_backend_list()` 里
  没有 `epoll`——事件循环退化成了 poll 后端；
- 或者 `TEVENT_NUM_SIGNALS` 被随手写成 64，信号数组边界差一位。

真正会报错的是**绕开 waf 之前的**那一步：

```
lib/replace/system/network.h:31:2: error: "AC_LIBREPLACE_NETWORK_CHECKS missing in configure"
lib/replace/replace.c:64:2:  error: "you must have a ftruncate function"
```

以及 wafsamba 的 mandatory 运行探针在只读 `/tmp` 上的失败。

## 根因分析

tevent standalone tarball 的构建入口是 `./configure && make`（waf 包装）。
在 OHOS worker 上不可直接用，因为 `wscript configure()` 会：

1. `RECURSE('lib/replace')` / `RECURSE('lib/talloc')` 并跑 wafsamba 的
   **mandatory** 运行探针——需要可写 `/tmp`，在只读 /tmp 或 HMDFS
   权限归一化环境下必失败；
2. 调用 `SAMBA_CHECK_PYTHON()` / `SAMBA_CHECK_PYTHON_HEADERS()`，
   引入与本包无关的 Python 探测；
3. 把 `lib/replace` 的完整 autoconf 特性矩阵写进 `config.h`——这份
   `config.h` 就是 `replace.c` 的前提，脱离它 `replace.c` 编不过
   （见同批 `rep_memset_s` 条目）。

于是走 direct-cc + `-DNO_CONFIG_H`。**代价是 wscript 里所有"探测后决定"
的东西都变成移植者的责任**，其中两类最容易出事：

### 陷阱一：源文件清单是条件式的

```python
SRC = '''tevent.c tevent_debug.c tevent_fd.c tevent_immediate.c
         tevent_queue.c tevent_req.c tevent_wrapper.c
         tevent_poll.c tevent_threads.c
         tevent_signal.c tevent_standard.c tevent_timed.c tevent_util.c tevent_wakeup.c'''

if bld.CONFIG_SET('HAVE_EPOLL'):
    SRC += ' tevent_epoll.c'
```

基础 14 个 + 条件 1 个。**漏掉 `tevent_epoll.c` 不会编译失败**——只是
后端注册表里少了 epoll，`tevent_context_init()` 回落到 poll。事件循环
照样跑、上游单测照样过（那两个测试不检查后端身份），于是退化被完全掩盖。
OHOS 是具备 `sys/epoll.h` 的，必须显式置 `HAVE_EPOLL` / `HAVE_SYS_EPOLL_H`
并把 `tevent_epoll.c` 列入源文件。

### 陷阱二：有些常量是运行探针算出来的

```python
tevent_num_signals = 64
tevent_num_signals = max(tevent_num_signals, NSIG, _NSIG, SIGRTMAX, SIGRTMIN * 2)
```

这不是"config.h 里有没有某个 flag"的问题，而是**探针代出来的一个数**。
在 OHOS 上：`_NSIG = 65`、`NSIG = _NSIG`，而 `SIGRTMIN` / `SIGRTMAX`
展开为运行时函数 `__libc_current_sigrtmin()` / `__libc_current_sigrtmax()`
——`CHECK_VALUEOF` 无法把它们折叠成编译期常量（探针拿不到值 → 视为 None）。
最终结果 **65**，必须由移植者手工落定。

## 解决方案

**主方案**: mirror-wscript-conditions-and-port-run-probe-constants

绕开 waf 之前，先把 `wscript` 的 `build()` / `configure()` 通读一遍，
把三类内容逐条抄进 direct-cc 配置：

| 抄什么 | tevent 0.17.1 的具体值 |
|--------|------------------------|
| (a) 基础源文件清单 | 14 个 `tevent*.c` |
| (b) 条件追加的源文件 + 判定宏 | `HAVE_EPOLL` → `tevent_epoll.c`（配 `HAVE_SYS_EPOLL_H`） |
| (c) 运行探针算出的常量 | `TEVENT_NUM_SIGNALS = 65`（来源 `_NSIG`） |

**验收必须用可观测行为，不能用"编译通过"。** 在 `test_package` 里调用
`tevent_backend_list()` 断言 `epoll` 在列表中——这样后端退化会变成
一次测试失败，而不是一个沉默的性能回归。本仓库的
`test_package/test_tevent.c` 就是这么写的（同时覆盖 immediate / timer /
fd 三类事件各投递一次、读到管道字节、事件循环有界收敛、
`talloc_free()` 能连 context 一起释放）。

**测试框架**：上游把 cmocka 放在 `third_party/cmocka` 随 tarball 分发，
直接编译该目录下的 `cmocka.c`（与上游 `CHECK_FOR_THIRD_PARTY` 分支一致），
不要引入外部 cmocka 包。两个上游单测（`test_tevent_tag` 5 例 /
`test_tevent_trace` 24 例）在 `build()` 内编译并运行；`bindings.py`
（pytevent CPython 扩展）因本包是纯 C 静态库而排除，需在 MANIFEST.yml
里显式声明为 excluded，不能静默丢弃。

**musl 小坑**：`third_party/cmocka/cmocka.h` 在 musl 上会重复
`typedef uintptr_t`（上游对 `_UINTPTR_T` 的守卫不完整），补
`-D_UINTPTR_T` 即可，不要改上游头文件。

## 验证

```sh
conan create archives/t/tevent/0.17.1 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing -nr

# 本地 OHOS native SDK 预验证（clang 15.0.4）
bash try4.sh
# tevent compile fails=0 / link ok test_tevent_tag / link ok test_tevent_trace
./test_tevent | grep -q "epoll backend present" && echo "后端未退化"
```

## 关联条目

- 与同批 `sys_errlist` 与 `rep_memset_s` 两条草稿构成"direct-cc 绕行 waf"
  三部曲：那两条讲**宏缺失引发的符号问题**，本条讲**条件与常量的人工落定**；
- 与仓库中 `tdb/1.4.15` 的 waf 补丁路线互为对照：tdb 选择打补丁让 waf
  跑通（需要改 mandatory 探针为致命性 + 跳过 python 测试），tevent 选择
  完全绕开 waf。两条路线都成立，取舍取决于 tarball 是否把 lib/replace
  的可探测面收敛到少数几个宏。
