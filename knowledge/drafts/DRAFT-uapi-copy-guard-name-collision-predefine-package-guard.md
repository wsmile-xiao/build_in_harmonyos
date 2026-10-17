# DRAFT-uapi-copy-guard-name-collision-predefine-package-guard：UAPI 头双副本守卫宏不同源，单 TU 交汇即定义重叠重定义

## 现象

消费者（触发案例：libnetfilter_queue 1.0.5，`conan create` → `make`）在编译
`src/nlmsg.lo` 时报 20+ 条重定义：

```text
error: redefinition of 'nfnetlink_groups'
error: redefinition of enumerator ...
error: redefinition of 'struct nfgenmsg'
note: previous definition of ...
```

同一翻译单元里可见两份同源 UAPI 头：

- sysroot：`<linux/netfilter/nfnetlink.h>`，守卫 `_UAPI_NFNETLINK_H`（设备实测）；
- 依赖制品：已发布 libnfnetlink/1.0.2 自带的 `<libnfnetlink/linux_nfnetlink.h>`
  （2008 年代内核头拷贝），守卫 `_NFNETLINK_H`（设备实测）。

## 根因

include guard 是预处理期按宏名的单副本去重机制，只对**同名守卫**的重复包含
生效。两份副本守卫宏**不同源**（`_NFNETLINK_H` vs `_UAPI_NFNETLINK_H`），
同一 TU 双 include 时后到副本整体展开，`enum nfnetlink_groups` /
`struct nfgenmsg` 等定义重叠，即重定义编译失败——`#include` 防重在
"不同守卫名"面前完全失效。

两份副本并非逐字相同（如 `NFNL_SUBSYS_COUNT`：制品=7、sysroot=12），
因此抑制哪一份是有语义的选择：应保留 sysroot 较新副本。

## 复发面（平台级，逐头实测）

OHOS sysroot（bionic 风格 uapi 快照）对**部分** UAPI 头保留 `_UAPI_` 守卫
前缀，与依赖制品内嵌副本的旧式守卫错开。设备实测：

| sysroot 头 | 守卫宏 | 前缀 |
|---|---|---|
| `linux/socket.h` | `_UAPI_LINUX_SOCKET_H` | 有 |
| `linux/netlink.h` | `_UAPI__LINUX_NETLINK_H` | 有 |
| `linux/netfilter/nfnetlink.h` | `_UAPI_NFNETLINK_H` | 有 |
| `linux/netfilter/nfnetlink_queue.h` | `_NFNETLINK_QUEUE_H` | **无（反例）** |

因此：**任何**依赖制品内嵌此类 UAPI 头拷贝、且同一 TU 还能看到 sysroot
同名头的项目即暴露；但复发面必须按"逐头实测守卫名"判断，不能按
"所有 UAPI 头都有 `_UAPI_` 前缀"推断（上表反例即是）。具体到 netfilter
家族，哪些后续消费者会与同一对头交汇，取决于其源码的实际包含链，
须逐项目核对，本文不做点名主张。

## 修复模式（rec）

消费者 TU 在交汇 include 前的守卫块预定义包内副本守卫宏（幂等写法），
抑制包内旧拷贝、保留先一步包含的 sysroot 较新副本：

```c
#include <linux/netfilter/nfnetlink.h>      /* sysroot 副本先进入 */

#ifndef _NFNETLINK_H
#define _NFNETLINK_H
#endif
#include <libnfnetlink/linux_nfnetlink.h>   /* 包内副本被守卫抑制 */
```

要点：

- 只对发生交汇的 TU 逐个落位；其余 TU 中包内副本仍是唯一来源，不受影响；
- 采用前须核对 sysroot 副本为较新/超集（本例 `NFNL_SUBSYS_COUNT`
  sysroot=12 > 制品=7 即为依据）；
- 修复以消费者源码补丁交付（对应原则 P-PATCH-001），按真实冲突条件
  （守卫宏名 + 包含链交汇）落位而非平台名分支（对应原则 P-PATCH-002）。

## 方案空间与权衡（fallback）

从包含链完全移除包内副本、只保留 sysroot 同名头。诚实权衡：

- 单纯调整 include 顺序对守卫宏不同源的双副本**无效**（后到者仍重定义）；
- 只有当包内副本仅经消费者直接 include 引入、无依赖头透传（如
  `libnfnetlink.h` 自身包含 `linux_nfnetlink.h`）时，"改用 sysroot 头"才
  成立，适用面窄；
- 根治方向是依赖配方侧统一守卫名，但跨消费者 run 边界，须由配方 owner
  独立承接，不属于消费者修复路径。

## 禁止动作（forbid）

1. **在依赖制品侧/sysroot 侧改守卫宏名**：已发布制品安装头与 sysroot 头
   不属于消费者 run 写入边界；改制品侧守卫会让同一制品在不同消费者之间
   行为分叉。后果：污染共享 conan 缓存/制品仓与平台 sysroot，跨 run 不可
   复现，以未改制品为前提的后续构建全部失效。
2. **经全局编译 flag 注入 `-D_NFNETLINK_H` 救单包**：会波及所有 TU——
   包内副本仍是唯一来源的 TU 一并被抑制。后果：交汇 TU 的重定义错误被
   替换为其余 TU 的 undeclared identifier 编译失败，问题被移动而非修复，
   且全局环境改动使构建失去可复现性。

## 验证证据（自包含探针，两段）

`verification_cmd`（见同名 .kv）可在设备任意新 shell 直接执行，不依赖任何
run 日志：

- **第一段（通用机理）**：两份仅守卫名不同（`_G_A`/`_G_B`）的最小头在同一
  TU 交汇，未预定义时编译必须失败且失败须为 redefinition；`-D_G_B` 预定义
  后编译、链接、运行全部通过。断言为 `return 0`（显式退出码，非 sizeof
  数值——sizeof 型断言会使进程以 4 退出，被误读为探针失败）。
- **第二段（真头复核）**：制品 include 目录（conan 缓存内 libnfnetlink 包）
  + sysroot 目录双路径。`r1.c`（sysroot nfnetlink.h + 制品 linux_nfnetlink.h）
  必须报 redefinition；`r2.c`（预定义 `_NFNETLINK_H`）必须编译运行通过。

每个失败分支都以 `FAIL-A`/`FAIL-B` 前缀显式 `exit 1`，不被管道或 `&&` 链
掩盖。两段探针的声称退出码：`stageA_exit=0`、`stageB_exit=0`、整体 `0`。

设备全新 shell 从 .kv 提取 `verification_cmd` 实跑记录（2026-09-09）：

```text
stageA_exit=0
stageB_exit=0
（整体退出码 0；失败分支探针另行验证会以 FAIL-* + 退出 1 结束）
```

说明：第二段引用的两个绝对路径（conan 缓存 glob `~/.conan2/p/*/p/include/`
与 SDK sysroot）为当前设备安装位置，属探针输入定位；缓存哈希目录或 SDK
升级后按 `ls $HOME/.conan2/p/*/p/include/libnfnetlink/linux_nfnetlink.h`
与 profile 内 SDK 路径重新定位即可。

## 关联

- similar_to：E091、E119（sysroot 内部两层头的 `sockaddr_storage` 重定义族，
  缺 `__UAPI_DEF_*` 协调，机理不同但同属 UAPI 双副本重定义错误面）、
  E163（sysroot 内核头非标语义）。
- principles：P-PATCH-001（修改以 .patch 交付）、P-PATCH-002（守卫隔离
  标准写法）。
- 触发事件：libnetfilter_queue 1.0.5 CI round-01（nlmsg.lo 重定义 ×20+），
  同轮 examples/nf-queue.c 同型交汇；最小修复随消费者补丁交付。
