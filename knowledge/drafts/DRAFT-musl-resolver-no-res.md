# DRAFT-musl-resolver-no-res - OHOS/musl 系 libc 无全局 `_res`/`res_ninit`

> 正式编号未分配；合并/提升时由知识库维护流程分配下一个可用 E###。

## 错误特征

autotools 项目在 OHOS（musl 风格 libc）上编译时出现：

- `use of undeclared identifier '_res'`
- `res_ninit` 探测链接失败（configure 走 `#else` 分支）
- `_res` 未声明 / `res_query` 隐式声明警告

## 触发条件

- 库源码的 DNS 查询代码引用 glibc 全局变量 `_res`（如 `_res.options |= RES_USE_DNSSEC`）。
- configure.ac 用 `AC_SEARCH_LIBS(res_ninit)` 探测，OHOS 上链接失败 → `#else` 分支编译 `_res` 代码。
- 典型项目：opendmarc（DMARC 策略库，`opendmarc_dns.c` 用 `res_search`/`res_query`）。

## 根因分析

glibc 的 `resolv.h` 声明全局 `struct __res_state _res` 与 `res_ninit()`；OHOS 的 `resolv.h` 是 musl 风格，**只提供** `res_init()`/`res_query()` 等函数，**没有** `_res` 全局变量，也**没有** `res_ninit()`。configure 探测 `res_ninit` 失败后，`#else` 分支对 `_res` 的引用在编译期报 undeclared identifier。这是 musl 系 libc 的通用兼容问题（glibc 有 `_res`，musl 没有），任何引用全局 `_res` 的 C/C++ 库在 OHOS 上都会踩到。

## 推荐方案

最小补丁：把 `#else` 分支中对全局 `_res` 的引用改为函数内局部 `struct __res_state resp`：

```c
struct __res_state resp;
(void) memset(&resp, 0, sizeof resp);
res_init();
#ifdef RES_USE_DNSSEC
resp.options |= RES_USE_DNSSEC;
#endif
answer_len = res_query(bp, C_IN, T_TXT, answer_buf, sizeof answer_buf);
```

要点：

- `struct __res_state` 在 OHOS `resolv.h` 有定义（`typedef struct __res_state {...}`），无需额外头文件。
- `res_init()`/`res_query()` 均存在，无需 `-lresolv`（OHOS 无独立 libresolv）。
- 只动引用 `_res` 的代码段，不改 configure 探测逻辑，补丁面最小。
- 断言/测试不受影响：`opendmarc` 实测 `make check` TOTAL 7 / PASS 7 / FAIL 0。

## 验证方法

1. `conan create` 编译通过（OHOS profile）。
2. 上游测试全过：opendmarc `make check` 7/7。
3. `readelf -d libopendmarc.so` 确认未链接额外 resolv 库。
4. 真机/CI 跑 DNS 查询路径无崩溃。

## 禁止事项

- ❌ 用 `#define _res` 宏掩盖：musl 上全局 `_res` 不存在，宏替换不解决符号缺失，且掩盖多线程安全问题。
- ❌ 尝试链接 `-lresolv`：OHOS 无独立 libresolv。

## 同类问题

- 任何引用 `_res`/`res_ninit` 的 DNS 代码（sendmail/milter 系、libspf2、opendkim 等）在 OHOS/musl 上编译失败的场景。

## 证据

- 触发：opendmarc 1.4.2（PR #6758），patch `0001-...-opendmarc_dns.c.patch`。
- 结果：`make check` 7/7 通过；conan-verify G0-G4 + L2/L4/L5 全 PASS；W4 审计 verdict=pass。
