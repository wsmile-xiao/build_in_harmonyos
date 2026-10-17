# inputlirc 34 for HarmonyOS

## 概述

inputlircd 是一个"零配置"的 LIRC 守护进程：它打开 Linux 的 `/dev/input/event*`
evdev 设备，把按键事件按 LIRC 文本协议写到一条本地 Unix 域套接字上，供 lirc 客户端
（`irw`、lircd 兼容程序）消费。本目录是它在 HarmonyOS PC (aarch64) 上的 Conan 配方。

## 软件信息

| 项目 | 值 |
|------|-----|
| 名称 | inputlirc |
| 版本 | 34 |
| 源码地址 | https://deb.debian.org/debian/pool/main/i/inputlirc/inputlirc_34.orig.tar.gz |
| 源码 sha256 | `6ff52376c226c7cb49fbe053365eb4931c97a9edfa503ee4ebb689598547270c` |
| 项目主页 | `https://git.sliepen.org/inputlirc`（取自 Debian `d/control` 的 `Homepage` 字段）——本窗 `curl -w "%{http_code}"` 实测 **404**，站根 `https://www.sliepen.org/` 实测 200 ⇒ 该字段是**发行版元数据声明，未经本窗可用性核验**，详见版本级 notes.md §6 |
| 许可 | GPL-2.0-only（`.orig` 包内不含 LICENSE 文件，授权声明见各源文件头部） |
| 构建系统 | 单个手写 `Makefile`，无 configure、无外部库依赖 |

## 鸿蒙环境

| 项目 | 值 |
|------|-----|
| 内核 | HongMeng Kernel 1.12.0，aarch64 |
| 编译器 | clang 15（`/data/service/hnp/bin/clang`，OHOS SDK sysroot） |
| 构建系统 | make（`make -j1`；HMDFS 上 jobserver 不可靠） |

## 编译与打包要点

上游对环境做了三个假设，在 HarmonyOS 上都不成立，配方逐一处理：

1. **内核 UAPI 头在 `/usr/include`**（补丁 0001）。上游 `Makefile` 把
   `/usr/include/linux/input-event-codes.h` 写成 `names.h` 的前置条件并作为
   `gennames` 的参数，`inputlircd.c` 里还有 `#include </usr/include/linux/input.h>`
   这条绝对路径尖括号包含。OHOS 的 UAPI 头在 SDK sysroot 内且路径含 SDK 版本号，
   因此改为可覆盖变量 `KERNELINC`，由配方在构建期问编译器要真实路径
   （`clang -M` 解析 `<linux/input-event-codes.h>`），源码侧只写 `<linux/input.h>`。
   `PREFIX`/`SBINDIR`/`MANDIR`/`DESTDIR` 本来就是 `?=`，无需改源码。
2. **镜像里有 `install(1)`**（补丁 0002 + 配方 shim）。HarmonyOS 无 coreutils
   `install(1)`，toybox `cp` 也不支持 `-m`，故 `package()` 生成一个 POSIX
   `install-sh` 并从 `INSTALL=` 注入，不改上游 install 规则。
3. **`make install` 落在 `$(PREFIX)/sbin`**。Conan 与 CI 的 L0k 都按 `bindirs`
   找可执行文件，因此打包时把 `SBINDIR` 指向 `<pkg>/bin`（打包布局决定，非源码改动）。

## 运行前提与已知限制（重要）

**本包能编译、能安装、`inputlircd` 能起来并按文档报错，但在当前 HarmonyOS PC
镜像上不能完成它的核心功能**：它拿不到输入设备，也建不起输出端点。三堵墙分别是
什么性质，见下（全部为真机 `open()`/`bind()`/`fork` 隔离探针实测）：

| 面 | 实测 | 性质 | 用户/部署怎么办 |
|----|------|------|-----------------|
| 输入：`/dev/input/event*` | **本 uid 下经 open()/glob() 不可判定**（sysfs 的 `/sys/class/input/event0` 与 `/proc/bus/input/devices` 佐证节点存在）：`open()` 对存在与不存在的节点名一律返回 `EACCES(13)`（父目录 `/dev/input` 本身即 Permission denied），而 `glob("/dev/input/event*")` → `GLOB_NOMATCH`（无法列目录） | **权限面**：需以能读 evdev 的身份运行（root 或 `input` 组），本环境无法自助提权，故 evdev `ioctl` 一律**未执行** | 只能在授权的设备上下文里实测；不要把 `GLOB_NOMATCH` 误读成"没有输入设备"，也不要把 `EACCES` 读成"节点存在" |
| 降权：`setuid` 族 | `setuid/seteuid/setgid/setegid/setresuid/setresgid/daemon/mlock` 全 OK；`setreuid/setregid` 被 **SIGSYS(31)** 杀 | **不构成阻塞**：inputlirc 只用 `setgid()`+`setuid()`，落在放行的一边 | 默认 `-u nobody` 在本机解析不到（`getpwnam` 返回 NULL，上游已判空并退 `EX_OSERR`）⇒ **必须显式 `-u <本机关联用户存在>`** |
| 输出：Unix 域套接字 | 默认 `-d` 值 `/run/lirc/lircd` → 目录不可建（`ENOENT`）；改指到可写目录 → `bind()` **`EPERM(1)`**；同目录建普通文件 OK、`mkfifo` 同样 `EPERM`、**抽象命名空间 `bind()` 成功** | **平台策略面**：拒的是"在文件系统上创建非常规 inode"，不是 AF_UNIX 子系统 | 上游 `-d` 只接受文件系统路径，无法用抽象命名空间 ⇒ 需要上游改造才能出功能，属路径 C，未自行开跑 |

因此：**不要**因为 `inputlircd` 装上了就认为遥控器链路可用；也**不要**把上面的
`EPERM` 当作"OHOS 不支持 Unix 套接字"——对照实验（抽象命名空间可用、TCP 回环可用）
已经否证了这种说法。

## 目录结构

```
archives/i/inputlirc/
├── README.md          # 本文件（软件级）
├── manifest.yaml      # 软件级
├── commands.json      # 软件级，R38/CI L0k
└── 34/
    ├── conandata.yml
    ├── conanfile.py
    ├── manifest.yaml  # 版本级
    ├── notes.md       # 症状→根因→最小复现→失败方案→最终方案→边界
    ├── patches/
    └── test_package/
```
