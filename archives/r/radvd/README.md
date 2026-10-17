# radvd

IPv6 路由宣告守护进程（Router Advertisement daemon）。实现 IPv6 邻居发现协议中的
路由宣告与默认路由器部分：对外周期发送 RA、下发前缀/默认路由/DNS(RDNSS/DNSSL)，
并附带 `radvdump` 抓包诊断工具。

- 主页：<https://github.com/radvd-project/radvd>
- 许可：BSD-4-Clause
- 类别：network / system daemon

## 已适配版本

| 版本 | 状态 | 说明 |
|---|---|---|
| 2.20 | built | 5 个 OHOS 移植补丁 + 上游 libcheck 测试 36/36 全绿 |

## 产物

`radvd`（守护进程）与 `radvdump`（诊断工具）两个可执行文件，无库产物
（`package_type = application`，故本目录带 `commands.json`，R38）。

## 平台注意事项

- RA 发送与 `radvdump` 抓包需要 `AF_INET6/SOCK_RAW/IPPROTO_ICMPV6`，
  在鸿蒙 PC 上因无 `CAP_NET_RAW` 返回 **EPERM** ⇒ 属**权限面**限制，
  需在具备该 capability 的执行环境下运行。
- configure 的 netlink 探测在 OHOS musl sysroot 上失败（`<sys/socket.h>` 与
  `<linux/netlink.h>` 同含导致 `sockaddr_storage` 重定义），`HAVE_NETLINK` 未定义，
  radvd 退回 ioctl/getifaddrs 分支 —— 这是上游 `configure.ac` 自身的降级分支。
- `radvd -v` / `-h` 会正确打印内容但以 **RC=1** 退出（上游约定），
  脚本化校验请按内容断言，不要按退出码。

细节见 `2.20/notes.md` 与 `2.20/reports/test-report.md`。
