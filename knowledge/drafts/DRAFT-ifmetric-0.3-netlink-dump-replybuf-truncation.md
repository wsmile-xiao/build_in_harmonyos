# ifmetric 0.3 — 遗留 netlink 工具固定 2KB replybuf：HarmonyOS PC 大 IFLA 属性接口致 dump 静默截断（draft）

**Category**: ohos | netlink | libc | runtime · **Severity**: 3 · **Tool**: netlink/recv/configure/make

## 症状

ifmetric 编译、签名、执行都正常，但**任何**调用都立刻失败，且报错发生在 netlink 层，
`socket()`/`bind()`/`send()` 全部没有报错：

```text
NETLINK: Packet too small or truncated! 728!=16!=1340
```

三个数字分别是 `recv()` 返回的剩余字节数、`sizeof(struct nlmsghdr)`、
以及当前 `p->nlmsg_len`。即"缓冲里还剩 728B，但这条消息自称要 1340B"。

因为 `getifn()`（RTM_GETLINK）是 ifmetric 的**第一个**动作，症状表现为
"程序一运行就挂"，非常容易被误判为"OHOS 不支持 netlink / 没权限"。
**本例两者都不是**：netlink 读路径在本机完全可用。

## 根因

1. 2004 年前后的独立 netlink 工具普遍把单次应答硬编码为小栈缓冲。ifmetric
   `src/nlrequest.c` 的 `netlink_request()` 用 `char replybuf[2048]` 收包，
   再用 `for (; bytes > 0; p = NLMSG_NEXT(p, bytes))` 在同一缓冲里遍历多条消息。
2. netlink 是**数据报**语义：内核把多条 `nlmsghdr` 打包进一个 skb，作为**一个**
   数据报投递。用户缓冲不够时 `recv()` **静默截断**并返回缓冲长度——不给
   `ENOBUFS`，不加 `MSG_TRUNC` 就完全无从得知被截断。
3. 于是缓冲尾部剩下一条"半截"消息：头部自称 1340B，实际只剩 728B，
   长度自检失败 → 打印上面的错误并 `return -1`。
4. HarmonyOS PC 命中概率远高于普通 Linux：真机 `/proc/net/dev` 有 14 个接口，
   其中华为无线类接口（`Hisilicon0/wlan0/wlan1/p2p0/chba0/nan0/ancowlan0`）
   携带大量 802.11 相关 `IFLA_*` 属性，**单条 `RTM_NEWLINK` 约 1340B**
   （普通以太网口约 76B）。整份 dump 实测 19276B。

## 实测证据（只读探针，独立于 ifmetric）

同一份 `RTM_GETLINK` dump，只改缓冲大小：

```text
type=18  buflen=  2048 recv_total= 14356 msgs=  7 truncated_datagrams=7
type=18  buflen= 65536 recv_total= 19276 msgs= 14 truncated_datagrams=0
type=26  buflen=  2048 recv_total=  1708 msgs= 22 truncated_datagrams=0
```

`truncated_datagrams=7` 且只收到 7 条（应为 14 条）——**每个数据报都被截断**。
第三行是 `RTM_GETROUTE`：本机只有 1708B，所以"只读路由表"的工具往往不显现此 bug，
别拿它当反证。

## 对策

不要用固定缓冲，**也不要**直接在收数据的 `recv()` 上加 `MSG_TRUNC` 然后
"发现不够就重试"——那种写法数据报**已经出队被消费**，重试读到的是下一个数据报，
会把中间整条消息静默丢掉，dump 结果不完整，比直接报错更糟。

正确姿势是两步——先**窥探**长度，再完整收取：

```c
#define NETLINK_REPLY_MIN 4096

/* MSG_TRUNC 让返回值是数据报真实长度；MSG_PEEK 保证不出队 */
want = recv(s, &probe, sizeof(probe), MSG_PEEK | MSG_TRUNC);

buflen   = (want < NETLINK_REPLY_MIN) ? NETLINK_REPLY_MIN : (size_t) want;
replybuf = malloc(buflen);
bytes    = recv(s, replybuf, buflen, 0);
/* ...原有遍历逻辑不变，每条 return 路径记得 free(replybuf)... */
```

这样对任意接口数量、任意属性大小都成立，不需要猜"多大够用"。
已落成 `patches/0001-netlink-dump-datagram-buf.patch`（`strip: 1`）。

**兜底方案**（不便动态分配时）：把缓冲放大到 64KB 量级**并**显式检测截断
（`recv(..., MSG_TRUNC)` 后比较返回长度与缓冲大小，超限就明确报错，
绝不继续遍历半截消息）。仅把 2048 改成 8192 治不干净——接口数与属性大小不受我们控制。

## 适用边界与反例

- **适用**：自带 netlink 收包循环的遗留工具（ifmetric、bridge-utils、老 iproute 派生、
  各类 vlan/bond 小工具），且目标机接口多或无线属性大。
- **不适用**：已用 libnl/libmnl 的包，它们内部已处理 dump 分页与动态缓冲。
- **不显现 ≠ 没问题**：只读 `RTM_GETROUTE` 且路由条目很少的工具在本机能侥幸通过，
  接口或路由一多即复现。
- **不要混条**：需要写路由（`RTM_NEWROUTE`/`RTM_DELROUTE`）的分支另需
  `CAP_NET_ADMIN`，与"读 dump 被截断"是两回事。
- **风险**：缓冲长度取自内核应答，必须做下限保护和 `malloc` 失败处理；
  接口极多时单次可能申请几十 KB（本例约 19KB，可接受）。

## 判别口诀

报错形如 `Packet too small or truncated! 剩余!=16!=声明长度`，
而 `socket`/`bind`/`send` **都没有报错** → 不是权限、不是内核不支持，
而是**接收缓冲太小**。先量一次真实 dump 大小再动手。

## 修复后验证

- `conan create`（ohos-aarch64）G0–G4 全绿；
- `test_package` 消费者测试 6/6（skipped=0）；其中
  `ifmetric hw2nosuchif0 5` 正确走到 `getifn()` 并打印
  `Interface 'hw2nosuchif0' not existent.`、退出码 1——证明
  `socket → bind → send → recv → RTA 遍历`整条读路径可用；
- 前后 `/proc/net/route` 逐字节一致，确认全程零改链。

## 查重与新增价值

知识库既有 netlink 命中 2 条，签名与解法均不同，故本条按 **create** 申报：

- **E091**：`linux/socket.h` 与 musl `sys/socket.h` 的 `sockaddr_storage`
  **重定义**（编译期），解法是 include 前 `#define` 改名守卫——编译面，非运行期收包。
- **E237**：HongMeng Kernel **缺** `/proc/acpi` 与 `NETLINK_GENERIC` 协议族
  （运行期能力缺失），解法是"编译验证 + 运行期降级/shim"——本条恰恰相反，
  netlink **能力是好的**，坏的是调用方的缓冲。

本条新增价值：给出"**内核可用但工具自毁**"这一类的通用判别路径
（先量化真实 dump 长度，再区分截断/权限/缺协议族三种成因），
以及 `MSG_PEEK|MSG_TRUNC` 两步法这个不依赖猜测缓冲大小的标准修法。
