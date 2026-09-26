# DRAFT: OHOS sysroot linux/prctl.h 与 sys/prctl.h 重复定义 struct prctl_mm_map

- **状态**: draft（待 promote 审核）
- **来源**: hashrat 1.25 适配（libUseful-bundled 5.45）
- **日期**: 2026-09-22

## 错误特征

```
/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin/../../sysroot/usr/include/sys/prctl.h:88:8: error: redefinition of 'prctl_mm_map'
struct prctl_mm_map {
       ^
/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin/../../sysroot/usr/include/linux/prctl.h:96:8: note: previous definition is here
```

## 根因分析

OHOS sysroot（musl + 内核 UAPI 头）中 `linux/prctl.h` 与 `sys/prctl.h` 均定义
`struct prctl_mm_map`。上游源码若先 `#include <linux/prctl.h>` 再
`#include <sys/prctl.h>`（如 libUseful-bundled/Process.c 的
`#ifdef HAVE_PRCTL` 块），第二个头触发 redefinition 编译错误。

与已入库的 E091/E119（sockaddr_storage 冲突）同类但符号与头文件不同：
- E091/E119：`linux/socket.h`（经 netlink/netfilter 引入）vs `sys/socket.h`，
  方案为 define-guard 临时重命名 struct 名。
- 本模式：`linux/prctl.h` vs `sys/prctl.h`，重命名 struct 无意义（冲突双方在同一
  TU 顺序引入，且 PR_* 常量仍需使用），正确方案是删除冗余的 `linux/prctl.h`。

## 修复方案（已验证）

删除 `#include <linux/prctl.h>` 引入（保留 `#include <sys/prctl.h>`）：

```c
#ifdef HAVE_PRCTL
/* OHOS: linux/prctl.h 与 sys/prctl.h 均定义 struct prctl_mm_map；
 * sys/prctl.h 已提供所需全部 PR_* 常量，省略 linux/prctl.h */
#include <sys/prctl.h>
#endif
```

关键事实依据：
1. OHOS `sys/prctl.h` 已包含 `PR_GET_DUMPABLE`、`PR_SET_DUMPABLE`、
   `PR_GET_NO_NEW_PRIVS`、`PR_SET_NO_NEW_PRIVS`（实测 grep 确认 4 项均在）；
2. 源码仅使用上述 4 个宏，无 `prctl_mm_map` 类型使用；
3. 删除后 make 全量编译通过，非 OHOS 平台（HAVE_PRCTL 分支保持原引入）行为不变。

## 验证

- 命令：`make -j2`（libUseful-bundled）→ 编译通过（此前在 redefinition 处失败）
- conan create（ohos-aarch64 profile）G2 通过
- 恢复验证：补丁仅 OHOS 平台宏守卫外层由 HAVE_PRCTL 条件包裹，非 OHOS 不受影响

## 适用边界 / 反例

- 适用：任何同时 include linux/prctl.h 与 sys/prctl.h 的 OHOS 源码（C/C++），
  且仅使用 PR_* 宏常量、不引用 prctl_mm_map 类型。
- 反例：若源码真实使用 `struct prctl_mm_map` 类型（如进程地址空间 dump 工具），
  不能直接删除 linux/prctl.h；需改用 define-guard 或 musl 兼容类型。

## 关系

- similar_to: E091（sockaddr_storage redefinition，linux/socket.h vs sys/socket.h）
- caused_by: OHOS sysroot 内核 UAPI 头与 musl libc 头重复定义（同一根因族）
- prerequisite_of: 无
- conflicts_with: 无
