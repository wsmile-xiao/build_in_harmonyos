# tevent 0.17.1（Samba lib/replace）`sys_errlist` 未定义符号的根修

> Draft: DRAFT-TEVENT-0171-MUSL-STRERROR-SYS-ERRLIST-REMAP
> Stem: `tevent-0.17.1-musl-strerror-sys-errlist-remap` — pairs with the same-stem `.kv`

## 基本信息

- **ID**: DRAFT-TEVENT-0171-MUSL-STRERROR-SYS-ERRLIST-REMAP
- **严重度**: 2
- **类别**: platform|portability|musl|replace-layer
- **触发工具**: conan|clang|ld|make|configure
- **阶段**: compilation|link

## 错误特征

编译期零报错（15 个 `tevent*.c` 全部干净通过），**链接期**才炸：

```
ld.lld: error: undefined symbol: sys_errlist
>>> referenced by tevent.c
>>>               tevent.o:(tevent_common_loop_wait) in archive libtevent.a
>>> referenced by tevent_epoll.c
>>>               tevent_epoll.o:(epoll_event_context_init) in archive libtevent.a
>>> referenced 9 more times
```

报错点全是 `strerror(errno)` 的调用位置，没有任何一条指向 `lib/replace/`。

## 根因分析

`lib/replace/replace.h:207` 有一条 glibc/Solaris 时代的兼容分支：

```c
#ifndef HAVE_STRERROR
extern const char *const sys_errlist[];
#define strerror(i) sys_errlist[i]
#endif          /* 实际是 #ifndef HAVE_STRERROR */
```

- `sys_errlist[]` 是 glibc 早期导出的错误码字符串数组（POSIX 早已废弃、
  glibc 2.32 后从公共头移除），**musl 从未导出过**；
- tevent/talloc/tdb/ldb 这些 Samba 家族库内嵌同一份 `lib/replace`，
  全库的 `strerror()` 都被这条宏重映射；
- 走完整 `./configure && make`（waf）时，wafsamba 的运行探针会把
  `HAVE_STRERROR` 写进生成的 `config.h`，所以**上游构建根本不会命中**；
- 一旦移植者为了绕开 waf（探针需可写 `/tmp`、需完整 `lib/replace`
  特性矩阵）改用 direct-cc + `-DNO_CONFIG_H`，就必须自己补齐
  waf 原本探测出来的每一个 `HAVE_*`，漏掉 `HAVE_STRERROR` 就得到这个符号。

错误信息与真实原因之间的落差（报 tevent.c、根在 replace.h、触发条件是
"少定义一个宏"）是这个坑最贵的地方：它不给出任何指向 replace 层的线索。

## 解决方案

**主方案**: define-have-strerror-and-both-strerror-r-guards

在 direct-cc 的 `COMMON_DEFINES` 里补上：

```
-DHAVE_STRERROR
```

同一文件里还有一条**姊妹陷阱**，必须一起处理：

```c
/* replace.h:645 */
#if (!defined(HAVE_STRERROR_R) || !defined(STRERROR_R_XSI_NOT_GNU))
#define strerror_r rep_strerror_r
int rep_strerror_r(int errnum, char *buf, size_t buflen);
#endif
```

条件是"两个宏任一缺失就重映射"。只定义 `HAVE_STRERROR_R` 并不解除重映射，
宏仍会把 `strerror_r` 指向本移植没有实现的 `rep_strerror_r`，留下第二个
悬空符号（当前 tevent 恰好没有调用点所以不报，属于运气）。正确做法是
**两个都定义**：

```
-DHAVE_STRERROR -DHAVE_STRERROR_R -DSTRERROR_R_XSI_NOT_GNU
```

修完后用 `llvm-nm -u` 复查归档，剩余未定义符号应当只有：

- libc/pthread（`read`/`write`/`epoll_ctl`/`pthread_mutex_*`/…）
- 库自身跨 `.o` 的符号（`tevent_common_*`、`_tevent_*`）
- `talloc_*`（由 `talloc/2.4.4` 依赖提供）
- `rep_memset_s`（由 compat 文件提供，见同批另一条草稿）

## 验证

```sh
# 本地 OHOS native SDK 预验证（clang 15.0.4, --target=aarch64-linux-ohos）
bash try4.sh
# tevent compile fails=0
# link ok  test_tevent_tag
# link ok  test_tevent_trace
llvm-nm -u libtevent.a | grep -E 'sys_errlist|rep_'
# 仅剩 U rep_memset_s（由 tevent_ohos_compat.o 满足）
```

CI（OHOS aarch64 原生 worker，profile `ohos-aarch64`）中
`conan create archives/t/tevent/0.17.1` 已在 `build()` 内编译并通过两个
上游 cmocka 单测。

## 关联条目

- 与 `rep_memset_s` 悬空符号同属"replace.h 宏展开引出的隐式依赖"一类，
  两条草稿应合并阅读；
- 与仓库中已有的 `cpmtools` / `dact` 等"手写 config.h 与 autoconf 产物
  对等性"条目同源：direct-cc 路线的核心风险就是把探测结果抄漏。
