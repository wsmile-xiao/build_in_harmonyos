# E547（draft）— Meson 单头 has_header 平台探测假阳性：用真实翻译单元组合探测修复探测逻辑

- **来源**: gupnp 1.6.10 HarmonyOS PC 适配
- **状态**: draft（待审，勿自行 promote）
- **关联**: 现象层见 E091（linux/socket.h 与 sys/socket.h 重定义 sockaddr_storage）

## 1. 现象

gupnp 1.6.10 顶层 `meson.build` 用 `cc.has_header('linux/rtnetlink.h')` 探测
netlink 可用性。OHOS 设备上该探测返回 **YES**，随后
`gupnp-linux-context-manager.c` 编译失败：

```
linux/socket.h:23:8: error: redefinition of 'sockaddr_storage'
sys/socket.h:377:8: note: previous definition is here
```

同时实测两个独立事实：

| 探测方式 | 结果 |
| --- | --- |
| `printf '#include <linux/rtnetlink.h>' \| clang -fsyntax-only -xc -` | 通过 |
| `printf '#include <sys/socket.h>\n#include <linux/netlink.h>\n#include <linux/rtnetlink.h>' \| clang -fsyntax-only -xc -` | 失败（redefinition） |

即：**单头探测是假阳性**。meson 的 `cc.has_header()` 把被测头放进独立最小编译
单元；`linux/netlink.h`（经 `linux/socket.h`）与 `sys/socket.h` 单独包含各自
都能过，同一翻译单元才冲突。真实源文件恰是后一种组合。

## 2. 根因

- 直接根因：OHOS musl sysroot 两个系统头重复定义 `struct sockaddr_storage`
  （E091 现象）。
- 本条目新增：**探测逻辑缺陷形态** —— meson 单头 `has_header` 无法表达"此头
  必须与 X 头共存"的真实约束；上游把它当作可用性判据时产生假阳性。

## 3. 修法（探测逻辑加固，非平台宏）

```meson
netlink_available = cc.has_header('linux/rtnetlink.h') and cc.compiles(
    '#include <sys/socket.h>\n#include <linux/netlink.h>\n#include <linux/rtnetlink.h>\nint main(void) { return 0; }\n',
    name: 'netlink headers usable together with sys/socket.h')
```

- 让探测试图包含与真实源文件**完全相同**的头组合；
- glibc 系通过（行为不变），OHOS 失败 → `netlink_available=false` →
  `gupnp-linux-context-manager.c` 不再编译、不加 `-DUSE_NETLINK`；
- 构建自动落到上游为非 netlink 平台维护的回退路径（gupnp 的 unix context
  manager，ifaddrs 实现，与 BSD 同路径）；
- 无 `__OHOS__` 平台宏（R8 合规）、无空 stub、无功能删减；上游可接受的正向
  探测改进。

反面教材（不采用）：给 C 源打 `#if !defined(__OHOS__)` 排除 netlink——把
适配绑在宏名上，且无法解释"探测通过但编译失败"，其他 musl 系平台不生效。

## 4. 验证证据（gupnp 1.6.10 实测）

- meson 日志并存：`Has header "linux/rtnetlink.h" : YES` +
  `netlink headers usable together with sys/socket.h: NO`；
- 修复后 `meson test` 7 程序 56 TAP 子用例全过；
- `readelf -d libgupnp-1.6.so` NEEDED = libsoup/libgssdp/libxml2/libc，
  无 netlink 残留；`gupnp_context_manager_create` 经 dlopen 实测返回
  unix context manager 实例（tests/context-manager 用例覆盖）。

## 5. 适用面与边界

- **适用**: meson 工程，任何"单头探测通过、与系统头同 TU 冲突"的特性探测；
  典型头集：`linux/netlink.h`、`linux/rtnetlink.h`、`linux/if_addr.h`、
  `linux/wireless.h` × `sys/socket.h`。
- **不适用**: autotools 的 `AC_CHECK_HEADER` 同样是单头探测，需对应改为
  `AC_COMPILE_IFELSE` 组合头探测；纯 CMake 用 `check_c_source_compiles`
  直接写组合 TU。
- **关联先例**: gssdp 1.6.6 遇到同一冲突但其上游没有独立探测（直接在源文件
  包含），当时采用 GSSDP_NO_NETLINK 能力宏打补丁；本条目是"上游有独立探测
  逻辑"场景下的更优解——修探测而非改源。
