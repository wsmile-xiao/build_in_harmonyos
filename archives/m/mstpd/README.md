# mstpd

Multiple Spanning Tree Protocol daemon —— Linux 桥接设备 STP/RSTP/MSTP（IEEE
802.1D / 802.1Q / 802.1s）用户态实现。

- 上游仓库：https://github.com/mstpd/mstpd
- 语言：C（另有若干 shell / python 辅助脚本）
- 构建系统：Autotools（configure.ac + Makefile.am + autogen.sh；发布归档内不含生成好的 configure）
- 许可证：GPL-2.0-or-later

## 产物

| 产物 | 类型 | 说明 |
|------|------|------|
| mstpd | 守护进程 | 生成树协议引擎，通过 netlink 与桥设备交互，BPDU 走 PF_PACKET 原始套接字 |
| mstpctl | CLI | 查询/配置桥与端口的 STP 参数，经 AF_UNIX abstract 套接字与 mstpd 通信 |
| bridge-stp | shell 脚本 | ifupdown 钩子，把网桥的 STP 使能/参数转成 mstpctl 调用 |
| mstp_config_bridge / ifupdown.sh / ifquery | 辅助脚本 | 装到 lib/mstpctl-utils（上游把 libexecdir 钉成 /lib，见 0.2.0 notes 适配点 7） |
| bash 补全、man 手册、bridge-stp.conf | 数据 | 随包安装 |

## 版本

| 版本 | 状态 | 说明 |
|------|------|------|
| 0.2.0 | built | HarmonyOS PC（aarch64）首个归档；构建与 CLI 面已验证，内核相关运行面见该版本 notes.md 的探针取证 |

## 适配要点

1. **必须自举**：官方 0.2.0 tag 归档只有 autogen.sh，配方用 autoreconf --install --force 生成 configure，
   因此 tool_requires automake/1.18 与 libtool/2.5.4（CI 干净环境只有 SDK 的 autoconf/autoreconf/m4/perl，
   没有 aclocal/automake/libtoolize）。
2. **主机三元组要显式钉**：OHOS 内核 sysname 报 HarmonyOS，config.guess 推不出主机类型，
   configure 的 --build/--host 一律显式给成 gnu 三元组，保持 native 语义（探测项真跑而不是退化成交叉默认值）。
3. **安装前缀必须给**：上游默认安装前缀落在本地 usr local 目录下，不是系统前缀，配方按 conan 的 package folder 前缀安装，
   并关掉 ifupdown 集成开关（它的 install hook 会往 /etc/network 下建符号链接）。
4. **依赖面干净**：configure.ac 只有 AC_CHECK_FUNCS(clock_gettime) 与 AC_SEARCH_LIBS(clock_gettime, rt)，
   没有 PKG_CHECK_MODULES 硬依赖、没有 AC_MSG_ERROR，因此本包无链式未发布依赖。
5. **运行面是平台能力问题**：mstpd 的实用价值来自操作内核 bridge（netlink RTM_* 、PF_PACKET BPDU、
   /sys/class/net 枚举、SIOCGIFBR 类私有 ioctl）。这些在 HarmonyOS PC 上的可用性逐项取证记录在
   版本目录 notes.md，构建通过不等于内核面可用，不虚构运行结论（口径同 E237 acpid 先例）。
