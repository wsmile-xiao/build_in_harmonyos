# DRAFT-10050: OHOS musl libc 声明了 `ns_name_ntop()` 却不实现，且根本没有 libresolv

- **来源**：wrapsrv 1.0.0 适配（2026-10-01）
- **阶段**：链接期（linking）
- **领域**：libc 差异（glibc/BIND → musl/OHOS）

## 现象

`wrapsrv`（DNS SRV 命令行包装器，单文件 C + 手写 Makefile）迁到 OHOS 后：

1. 去掉链接错误后编译干净，链接报
   ```
   ld.lld-15: error: undefined symbol: ns_name_ntop
   >>> referenced by wrapsrv.c
   ```
2. 上游 Makefile 写死 `LDFLAGS = -lresolv`，报 `cannot find -lresolv`。

在 glibc / macOS 上从来不会遇到——它们自带 BIND libresolv。

## 根因：musl 把 resolver 内联进 libc，同时砍掉了 BIND 私有的 `ns_*` 名字 API

musl 的 `<arpa/nameser.h>` 直接抄了 BIND 的头，声明了 `ns_initparse()`、
`ns_parserr()`、`ns_name_ntop()`、`ns_skiprr()`。实测 OHOS sysroot 里
`llvm-nm --defined-only usr/lib/aarch64-linux-ohos/libc.a` 得到的
`ns_/dn_/res_` 符号全集：

```
ns_get16  ns_get32  ns_initparse  ns_name_uncompress  ns_parserr
ns_put16  ns_put32  ns_skiprr
dn_comp   dn_expand  dn_skipname
res_bind_socket  res_init  res_query  res_querydomain  res_search  res_send
__res_mkquery  __res_msend  __res_msend_rc  __res_send  __res_state
```

**没有 `ns_name_ntop`**，也**没有任何 `libresolv`**（sysroot 里
`find -name '*resolv*'` 为空）。musl 提供的是 `ns_name_uncompress()` /
`dn_expand()` 这一族，而不是 BIND 的 presentation-format 渲染器。

于是任何调用 BIND「wire 格式域名 → 文本域名」函数的老 DNS 工具，
在 OHOS 上都会编译干净、链接失败。

## 修复（两处，**都不引入平台宏**，PF5/R8 合规）

1. **丢掉 `-lresolv`**：在 recipe 里覆盖 Makefile 变量
   `make CC=<conan conf 的 c> LDFLAGS=`。
   不丢任何功能——`res_query()` / `ns_initparse()` / `ns_parserr()`
   本来就是 libc 符号。
   *不要*用「再堆一个 `-lresolv`」这种试探式加参数。

2. **树内补一个 RFC 1035 线格式渲染器**替换 `ns_name_ntop()` 调用点：
   - 逐 label 读长度字节，`> NS_MAXLABEL` 即报错；
   - `0xc0` 掩码视作压缩指针，校验「必须指向更早位置」——
     这同时天然给出了循环上界（因此不会死循环）；
   - 去掉末段尾点，根域名输出 `.`；
   - 每段写入前按 `buflen` 检查 `len + label + 2 > buflen`，不会溢出
     `target_name()` 里的 `char buf[NS_MAXDNAME]`；
   - 返回值语义与 BIND 一致（`-1` 失败，否则为 presentation 长度），
     调用点的 `perror()` 标签同步改名。

   这样在 glibc 上语义完全等价，对非鸿蒙平台透明。

> SRV rdata 的 target 按 RFC 1035 §4.1.4 / RFC 2782 **不允许压缩**，
> 所以真实场景走非压缩分支。压缩分支是防御性的；且必须说明它以「传入指针
> 为基准」解释偏移——上游把 `ns_rr_rdata()` 的裸指针当 `ns_name *` 传入，
> 本身就没有可用的报文基址。

## 排查口诀

> 老 DNS 工具在 OHOS 上链接失败、报的却是 `ns_*` / `dns_*` 符号，
> 基本都是这一条。先拿到 OHOS **真实有**的符号全集再决定补什么：

```bash
llvm-nm --defined-only <sysroot>/usr/lib/aarch64-linux-ohos/libc.a \
  | grep -oE '\b(ns_|dn_|res_)[a-z_0-9]+' | sort -u
```

不要凭 glibc 经验猜「musl 应该有」。

## 三段式证据链（本条已实测）

| 步骤 | 结果 |
|------|------|
| 不打补丁直接编译 | `ld.lld-15: error: undefined symbol: ns_name_ntop`，无二进制产出；手工去掉 `-lresolv` 后**仍然**失败（证明两处必须都改） |
| 打补丁 + `LDFLAGS=` | 在上游自带 `-Wall -Wextra -Werror` 下**零告警**编过，产出 aarch64 ELF 可执行文件 |
| 消费者用例 | `test_package` 对**交付二进制**跑 **27 项断言全过**（`TOTAL=27 PASS=27 FAIL=0`） |

其中 `%h` 替换的期望值 `primary.example.com` **只能由正确的 wire→text 转换产生**，
即补丁本身被真实执行并被断言到。

**变异验证（5 组，全部被杀死）**：

| 变异 | 被杀断言数 |
|------|-----------|
| 删掉 `bin/wrapsrv` | 23 |
| 应答 target 改名 | 4 |
| 应答端口 8080→1234 | 2 |
| priority-10 改成 priority-30 | 3 |
| 应答 rdlength 改成 4 | 9 |

## 适用范围

- 调用 BIND 私有 `ns_*` / `dns_*` API 的老 DNS 工具与服务
- Makefile 里写死 `LDFLAGS = -lresolv` 的 C 项目
- 任何 `#include <arpa/nameser.h>` 且使用 `ns_initparse` / `ns_parserr` / `ns_msg_*` 的程序

## 关联文件

- `archives/w/wrapsrv/1.0.0/patches/0001-replace-ns_name_ntop-with-portable-wire-name-renderer.patch`
- `archives/w/wrapsrv/1.0.0/notes.md`（问题表 1/2/3、变异验证表）
- `archives/w/wrapsrv/1.0.0/test_package/test_wrapsrv.sh`、`test_package/res_stub.c`
