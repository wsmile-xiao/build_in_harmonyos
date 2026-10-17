# l2tpns

## 简介

l2tpns 是一个高性能的 L2TP 网络服务器（LNS，Layer 2 Tunneling Protocol
Network Server），面向运营商级拨号汇聚场景：终结 L2TP 隧道与 PPPoE 会话、
对接 RADIUS 认证/计费、提供流量整形（tbf）、walled garden、snoop、BGP 等
能力，并通过内嵌的 Cisco 风格 CLI（libcli，tcp/23）与 `nsctl` 控制工具做
运维管理，另带 8 个可动态加载的 CLI 插件。

## OHOS 适配（2.5.0）

- 上游为手写 Makefile 工程（无 configure），配方经 make 命令行注入
  `CC/INCLUDES/LDFLAGS/l2tpns.LIBS/EXTRA_CFLAGS`，并以 `-j1` 串行构建
  （鸿蒙 SELinux 禁止用户进程创建 FIFO，GNU make 的 jobserver 依赖
  FIFO 传递并行令牌，并行 make 会卡住或报错）。
- 依赖 `libcli/1.10.7`（静态）：守护进程以显式 `.a` 绝对路径链接，产物
  `DT_NEEDED` 仅 `libc.so`；`l2tpns.LIBS` 覆盖去掉 `-ldl`（musl 自带
  dlopen/dlsym）。
- `ohos_compat.h`（`EXTRA_CFLAGS=-include` 注入）解决 OHOS SDK 净化版
  uapi 头与 musl 头的 `sysinfo`/`sockaddr_storage`/`ethhdr` 重复定义，
  并补 `__kernel_sa_family_t` 与 `__packed`（E119 家族，同 batctl）。
- `cli.c`/`cluster.c` 补 `<fcntl.h>`；`struct msghdr` 改指定初始化器
  （OHOS musl 布局 `int msg_iovlen` + pad）。
- 绝不执行 `make install`（硬编码 `install -o root -g root`、gzip man、
  `mknod /dev/net/tun`，E108）：逐产物 copy 交付 `bin/l2tpns`、
  `bin/nsctl`、`lib/l2tpns/*.so`（8 个插件）与 `licenses/COPYING`。
- 上游无测试套件（根 Makefile 无 check/test；上游 CI 仅
  `scripts/ci-test.sh`；`test/` 为需真实 LNS/LAC 拓扑的负载模拟工具），
  test_package 新增 6 项 OHOS 特有断言/门禁（见 notes.md）。

## 运行期说明

- 完整数据面运行需要 root/CAP_NET_ADMIN、`/dev/net/tun`、内核 L2TP
  （genetlink）或 PPPoE 与 `/etc/l2tpns/startup-config`。真机实测：
  内核 L2TP 缺失已坐实（`/proc/net/protocols` 无 l2tp 条目、
  `/proc/net/genetlink` 不存在）；`/dev/ppp` 节点存在（root:root 660，
  非 root 不可 open）；`/dev/net` 目录存在但不可遍历（tun 节点存在性
  未证实）。完整数据面当前不可运行，如实声明、不虚构可运行结论。
- 二进制本身在 OHOS 真机可加载可执行（test_package usage 路径门禁验证）。
- `garden.so` 运行期依赖 iptables（OHOS 缺失时该插件功能降级）。

## 依赖

- `libcli/1.10.7`（静态链接进 l2tpns 守护进程；插件 dlopen 仅依赖 libc）。

## 功能验证

```bash
# test_package 自动执行：
./l2tpns --version          # usage 路径，exit 0（不启动守护进程）
./test_l2tpns <pkg_folder>  # 6/6 PASS（TAP 输出，失败即非零退出）
```
