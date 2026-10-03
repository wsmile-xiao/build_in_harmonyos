# HarmonyOS 沙箱拒绝 netlink bind 时的运行期接口枚举回退（getifaddrs）

## 场景

kea-hook-ha 3.0.3（ISC Kea 的 High Availability hook）在 OHOS aarch64 上
`conan create`，`build()` 内 `meson test` 实跑上游两套件
`dhcp-ha-lib-tests`（443 例）+ `dhcp-ha-libload-tests`（7 例）。

首轮 443 例中 **48 例 FAIL**，全部是 `HAServiceTest.*`；libload 7 例全过。

## 症状

```
[ RUN      ] HAServiceTest.sendHeartbeat
ha_service_unittest.cc:907: Failure
Actual: it throws isc::dhcp::IfaceDetectError with description "Failed to bind netlink socket."
```

失败堆栈链（Kea 3.0.3 源码）：

1. `ha_service.cc` 建伙伴连接（clientConnectHandler）时调用
   `IfaceMgr::instance().addExternalSocket(tcp_native_fd, ...)` —— 生产路径，
   不是测试专属；
2. `IfaceMgr` 构造（`iface_mgr.cc:206`）→ `detectIfaces()`；
3. Linux 实现（`iface_mgr_linux.cc`）**唯一路径**是 netlink：
   `Netlink::rtnl_open_socket()` → `socket(AF_NETLINK)` 成功后立即显式
   `bind()` → 被沙箱拒绝 → `isc_throw(Unexpected, "Failed to bind netlink socket.")`；
4. 构造中的 catch 把它重抛为 `IfaceDetectError`（`iface_mgr.cc:208-210`）。

任何构造 `IfaceMgr` 的进程（kea-dhcp4/6 服务端、48 个发心跳/同步类用例）
都会死在这一步；纯逻辑用例不构造 IfaceMgr，所以同一个套件"一半过一半挂"。

## 根因

HarmonyOS app 沙箱对 AF_NETLINK 套接字**只放行创建与（无 bind 的）
sendto/recvfrom**：`socket(AF_NETLINK, SOCK_RAW, NETLINK_ROUTE)` 返回 fd，
但显式 `bind()` 返回 EPERM。

真机沙箱探针（python，逐项取证）：

| 能力 | 结果 |
|------|------|
| `socket(AF_NETLINK, SOCK_RAW, NETLINK_ROUTE)` | ✅ 成功 |
| 该 socket 上显式 `bind()` | ❌ 被拒（EPERM） |
| `getifaddrs()` | ✅ AF_PACKET 13 条（MAC/hatype，含 lo/dummy0/tunl0/Hisilicon0/wlan0 等）+ v4/v6 地址条目；`if_nameindex` 列出 19 个接口 |
| `if_nametoindex` / `ioctl(SIOCGIFADDR・SIOCGIFFLAGS・SIOCGIFINDEX)` | ✅ 全部成功 |
| `/proc/net/dev` | ❌ Permission denied（普通用户） |

即 **libc 的枚举路径整体可用**（musl 的 getifaddrs 内部不显式 bind，直接
sendto 内核），被封的只有"显式 bind 的持久 netlink 套接字"这一种用法。
Kea 的 BSD/Solaris 实现本来就是 getifaddrs 路线，Linux 实现才是纯 netlink。

## 怎么快速看出来

```bash
# 症状一句话定位（meson test 日志）
grep -m1 "Failed to bind netlink socket" <build_folder>/meson-logs/testlog.txt
# 沙箱能力三连（设备上直接跑）
python3 -c "import socket; s=socket.socket(16,3,0); print('socket ok'); s.bind((0,0))"   # 只有这行报错
python3 -c "import socket; print(len(socket.if_nameindex()), 'ifaces')"                  # 正常
```

可区分性：这是**运行期 bind 被拒**——与 E091（编译期 netlink 头冲突，
`redefinition of 'sockaddr_storage'`）和 E237（NETLINK_GENERIC 事件源在
受限内核下不可用）都不同面，但同属"netlink 在受限环境下的路径选择"家族。

## 修复

**能力探测 + getifaddrs 回退**（不引入平台宏，回退只在 netlink 打不开时生效）：

```cpp
// iface_mgr_linux.cc detectIfaces()：netlink 打开包 try/catch
try {
    nl.rtnl_open_socket();
} catch (const std::exception&) {
    detectIfacesByIfaddrs(update_only);   // 两趟遍历：先建接口，再补 MAC/地址
    return;
}
```

回退体照上游自带 `iface_mgr_bsd.cc` 改写为 Linux 变体：

- 两趟 `getifaddrs()`：第一趟按接口名建 `Iface`（`if_nametoindex` 索引 +
  `setFlags(ifa_flags)`）；第二趟按 `ifa_addr->sa_family` 分派——
  `AF_PACKET` → `setHWType(sll_hatype)` + `setMac(sll_addr, sll_halen)`；
  `AF_INET`/`AF_INET6` → `addAddress(IOAddress::fromBytes(...))`；
- 注册循环与主路径同语义（`update_only` 时走 `getIface` 更新，否则
  `addInterface`）。

常规 Linux 上 netlink 正常，回退分支永不触发 —— 对宿主/桌面构建零影响；
OHOS 上源码打补丁后本组件 443/443 + 7/7 全绿（此前 48 FAIL）。

实例补丁：`archives/k/kea-hook-ha/3.0.3/patches/0005-src-lib-dhcp-iface_mgr_linux-getifaddrs-fallback.patch`

## 边界

- 若更严的沙箱连 `getifaddrs()`/ioctl 也拒绝：按"接口枚举不可用"明确上报或
  短路相关功能，**不要静默返回空接口表**——DHCP 服务在空接口表上会以错误
  配置继续运行，比启动失败更难排查。
- 不要往提权方向修（sudo/CAP_NET_ADMIN/setcap）：CI 与真机包构建环境都无
  提权途径，且沙箱拒绝 bind 是设计行为。

## 关键词

`netlink`, `AF_NETLINK`, `NETLINK_ROUTE`, `bind`, `EPERM`, `rtnetlink`,
`getifaddrs`, `if_nametoindex`, `SIOCGIFADDR`, `IfaceMgr`, `kea`, `dhcp`,
sandbox, interface enumeration, `Failed to bind netlink socket`

## 相关条目

- **E091** —— netlink 区域的编译期头冲突（`sockaddr_storage` 重定义）；
  本条是同一区域的运行期 bind 面，两者可同时出现在一个包上
- **E237** —— 受限内核缺 NETLINK_GENERIC 致事件源不可用（设施缺失的降级范式）
- **E429** —— /proc/diskstats 仅 root 可读的代码级优雅降级（同属"运行期能力
  受限 → 明确回退"范式）
- **DRAFT-libnm-1.52.1-upstream-test-harness-false-negatives**（未编号草稿）——
  沙箱 seccomp 直接拒绝 NETLINK_ROUTE socket（`Bad system call`）；与本条
  "放行创建、拒绝 bind"是同一受限面的两种档位
