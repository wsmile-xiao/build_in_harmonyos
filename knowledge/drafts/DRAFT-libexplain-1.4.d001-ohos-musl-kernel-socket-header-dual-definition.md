# DRAFT-libexplain-1.4.d001-ohos-musl-kernel-socket-header-dual-definition：OHOS SDK 内核 socket 头与 musl 双向不互认，同 TU 必重定义 `sockaddr_storage`

> Contributor: sunjunyang | Status: Draft | Updated: 2026-09-21
> Source: libexplain 1.4.d001 适配（本配方 PR），触发文件 `libexplain/buffer/ifreq_data/hwtstamp_config.c`
> 对应：`knowledge/drafts/DRAFT-libexplain-1.4.d001-ohos-musl-kernel-socket-header-dual-definition.kv`

## 现象

同一翻译单元里 musl `sys/socket.h` 与 SDK 内核 `linux/socket.h` 双头交汇时，
**无论 include 顺序如何**都编译失败（设备实测，OHOS SDK 26 sysroot）：

```console
t1.c:2:1: 先内核后 libc：
sysroot/usr/include/sys/socket.h:377:8: error: redefinition of 'sockaddr_storage'
sysroot/usr/include/linux/socket.h:23:8: note: previous definition is here

t2.c: 先 libc 后内核（仅调序）：
sysroot/usr/include/linux/socket.h:23:8: error: redefinition of 'sockaddr_storage'
sysroot/usr/include/sys/socket.h:377:8: note: previous definition is here
```

触发不需要任何 socket 调用——纯头文件交汇即炸。libexplain 的交汇路径：
`libexplain/ac/net/if.h`（→ musl `sys/socket.h`）与
`libexplain/ac/linux/net_tstamp.h`（→ 内核 `linux/socket.h` 链）。

## 根因

平台 sysroot 里有两份 socket 头：musl libc 自己的 `sys/socket.h`，和内核
uapi 快照的 `linux/socket.h`。内核头的防重设计依赖 `linux/libc-compat.h`
**只对 glibc** 的握手：它探测 glibc 专有宏组合来决定 `__UAPI_DEF_*` 系列开关。
musl 的 `sys/socket.h` 没有经典可见守卫宏（经 `bits/alltypes.h` 的
`__NEED_*` 机制供型），不在 libc-compat 的识别表里——握手永不触发，
开关全按默认"要定义"走。

结果：两份头守卫宏**根本不同名**（内核 `_UAPI_LINUX_SOCKET_H`，musl 侧无
同名守卫），`#include` 的防重机制在"不同守卫名"面前完全失效，谁先谁后都
各自展开一次 `sockaddr_storage`。内核头的内容 musl 已全覆盖，抑制内核副本
没有任何语义损失。

## 设备实测证据（4 组合探针，2026-09-21）

最小 TU：

```c
#include <sys/socket.h>
#include <linux/socket.h>
int main(void){ struct sockaddr_storage s; return (int)sizeof(s); }
```

| 组合 | 结果 |
|---|---|
| T1 内核头在前 | ❌ redefinition（musl:377 vs 内核:23） |
| T2 仅调序（libc 在前） | ❌ 仍 redefinition（顺序救不了） |
| T3 libc 在前 + `-D_UAPI_LINUX_SOCKET_H=1` | ✅ 编译运行通过，退出码 = `sizeof(sockaddr_storage)` = 128 |
| T4 libc 在前 + `-D__UAPI_DEF_SOCKADDR=0` | ❌ 无效——开关只在 glibc 握手激活 libc-compat.h 后才被读，musl 下握手不进 |

守卫名实测：内核 `linux/socket.h` 第 19-20 行
`#ifndef _UAPI_LINUX_SOCKET_H / #define _UAPI_LINUX_SOCKET_H`。

## 方案（推荐 ①，视侵入面可用 ②）

**① 全局预定义内核守卫（配方/构建系统层）**

```sh
CPPFLAGS="-D_UAPI_LINUX_SOCKET_H=1 ${CPPFLAGS}"
```

配合把 musl 头排到内核头之前（源码 include 顺序补丁——顺序在语义上仍值得
固定，但真正起效的是预定义，见 T2/T3 对照）。

**全局注入在本场景是安全的**：被抑制的对象是平台 libc 的冗余副本，musl 是
全平台每个 TU 的 libc，不存在"内核副本是某 TU 唯一来源"的情形。

**② 逐 TU 守卫块（不便动全局旗标时）**

在交汇 TU 的内核头 include 前写幂等三行：

```c
#ifndef _UAPI_LINUX_SOCKET_H
#define _UAPI_LINUX_SOCKET_H
#endif
#include <linux/net_tstamp.h>   /* 内核副本被守卫抑制 */
```

代价：每个交汇 TU 都要补一处，漏一处即复发。

## 禁止动作

1. **注入 `-D__UAPI_DEF_SOCKADDR=0` 等 UAPI_DEF 开关**：实测无效（T4），
   只会制造"已处理"的错觉，构建依旧报 redefinition。
2. **改/删 sysroot 里的内核头**：sysroot 是平台共享资产，影响所有消费者，
   且 SDK 升级即被冲掉。

## 与 DRAFT-uapi-copy-guard-name-collision-predefine-package-guard 的边界

同族不同案，**结论表面相反，判据统一**——"被抑制副本是否可能是某 TU 的
唯一来源"：

| | uapi-copy-guard 条目 | 本条 |
|---|---|---|
| 两份头所有权 | sysroot uapi 副本 vs **依赖制品内嵌**旧拷贝 | sysroot uapi 副本 vs **musl libc 自带** `sys/socket.h` |
| 制品/内核副本地位 | 可能是部分 TU 的唯一来源 | 恒为冗余（musl 全覆盖） |
| 全局 `-D` | ❌ 禁止（会误伤"唯一来源"TU） | ✅ 安全且必要 |
| 逐 TU 守卫 | ✅ 推荐 | ✅ 可用（fallback） |

## 验证命令

```sh
printf '#include <sys/socket.h>\n#include <linux/socket.h>\nint main(void){ struct sockaddr_storage s; return (int)sizeof(s); }\n' > t.c
clang -D_UAPI_LINUX_SOCKET_H=1 -o t t.c && ./t; echo $?
# 期望：输出 128（musl 版 sockaddr_storage 尺寸），退出码 128
```
