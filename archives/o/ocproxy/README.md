# ocproxy

`ocproxy` 是一个基于 lwIP 的用户态 SOCKS5 代理与端口转发工具，配合 OpenConnect 的
`--script-tun --script` 使用。它让 VPN 客户端的网络流量不再「劫持」整机路由：只有显式
要求代理的连接才会走 VPN 隧道，其余流量仍走本机网络。同一版本还附带实验性的 `vpnns`，
用 Linux 命名空间把单个应用放进独立网络环境。

## 功能概述

- `-D <port>`：在内置 lwIP 协议栈上开一个 SOCKS5 服务端，支持 `CONNECT` 命令。
- `-L <lport>:<rhost>:<rport>`：本地端口转发，把 `localhost:lport` 的连通过隧道送到
  `rhost:rport`。
- 通过 `VPNFD` 环境变量接收 openconnect 传来的隧道文件描述符，网络参数取自
  `INTERNAL_IP4_ADDRESS` / `INTERNAL_IP4_MTU` / `INTERNAL_IP4_DNS` / `CISCO_DEF_DOMAIN`。
- `vpnns`：在新建的 user/uts/net/mnt 命名空间里运行一个命令，或 `--attach` 接入已有命名空间。

## OHOS 适配

完整说明见 `1.6/notes.md` 与 `1.6/manifest.yaml`。要点：

1. 上游 tarball 是纯 autotools 源码，没有 `configure`/`Makefile.in`，配方需自行
   `autoreconf --force --install`。
2. `config.guess` 不认识 HarmonyOS，且设备上没有 `cc` 供它探测，`configure` 会直接以
   `cannot guess build type` 失败。`config.sub` 认识 `aarch64-linux-ohos`，因此配方显式传
   `--build=aarch64-linux-ohos --host=aarch64-linux-ohos`（两者相同，保持 native 语义，
   不引入交叉编译三元组分支）。
3. HMDFS 的目录语义会让 autoconf 的 `(umask 077 && mktemp -d)` 私有临时目录落盘为 2700、
   创建者自己都写不进去，`config.status` 报 `Permission denied`；补丁去掉该 umask。
4. `vpnns` 依赖 GNU 专有的 `get_current_dir_name()`，OHOS libc 没有该符号，改用
   `getcwd(NULL, 0)`。
5. 上游两个二进制都没有 `--version`/`--help`，补丁按上游 `vpnns` 已有的写法补上
   `-V/--version` 与 `-h/--help`，便于打包与冒烟检查在无隧道环境下识别产物；同时修掉
   `vpnns` 无参时在命名空间创建路径上的段错误。

## 依赖关系

- 编译期：`libevent/2.1.13`（已发布到 ohpcd，OHOS binary 可用）；构建工具 `automake/1.18`
  （`tool_requires`，提供 `autoreconf` 需要的 `aclocal`/`automake`，不进入运行期依赖链）。
- 运行期：`libevent` 的 4 个 `.so`（`libevent`、`libevent_core`、`libevent_extra`、
  `libevent_pthreads`）必须在加载器搜索路径上；conan 的 `conanrun` 环境已注入。
- `lwIP` 与 `lwIP unix contrib port` 随上游 tarball 一起提供，不需要外部依赖。

## 已知限制

- `vpnns` 需要内核支持 user/net/uts/mnt 命名空间与 `mount()`，且通常需要特权；打包与测试
  只验证其 CLI 与可加载性，不做命名空间端到端运行。
- 上游没有自动化测试套件（详见 `1.6/reports/upstream-test-inventory.md`）。

## 参考资料

- 上游仓库：<https://github.com/cernekee/ocproxy>
- 版本 tag：`v1.60`（`configure.ac` 内声明为 `1.60`，任务卡版本为 `1.6`）
- 源码镜像：<https://deb.debian.org/debian/pool/main/o/ocproxy/ocproxy_1.60.orig.tar.gz>
  （与 GitHub archive 逐字节一致，sha256 `a7367647f07df33869e2f79da66b6f104f6495ae806b12a8b8d9ca82fb7899ac`）
