# QuickTun 2.2.6 - HarmonyOS PC 适配记录

## 概述

QuickTun 是一款极简的 VPN 软件：它把流量装进一条**基于 UDP 的加密隧道**，隧道两端各挂
一个 tun/tap 网络接口。加密由 libsodium 提供（Curve25519 + XSalsa20 + Poly1305），
上游作者 Ivo Smits（UCIS 组）。它是**守护进程/命令行工具**，不是库。

**编译状态**: ✅ 编译通过、打包通过、消费者测试通过 ｜ ⚠️ **运行受限**：守护进程主路径
需要 `/dev/net/tun`，在构建主机上该节点**存在但 `open()` 被拒（EACCES）**，因此隧道
功能无法在本机实测；包内不依赖 TUN 的路径（`quicktun.keypair` 密钥派生）已实测通过。

## 编译环境

| 项目 | 值 |
|------|-----|
| 系统 | HarmonyOS HongMeng Kernel 1.12.0 aarch64 |
| 编译器 | clang 15.0.4（`/data/service/hnp/bin/clang`） |
| C 库 | musl libc（`aarch64-linux-ohos`） |
| Conan profile | `ci/conan/profiles/ohos-aarch64` |
| 依赖 | libsodium/1.0.22（ohpcd 已发布，recipe + binary 均实测可下载） |

## 构建系统的特殊性

QuickTun **没有 configure、没有 Makefile、没有任何构建系统文件**。唯一入口是仓库根的
`build.sh`（90 行）：它用一条条裸 `cc` 命令把 `src/` 下的 `.c` 直接编成 `out/` 里的
各个可执行文件，并且**没有 install 目标**。因此本配方必须：

1. 自己驱动 `build.sh`（而不是 `Autotools.configure()/make()`）；
2. 自己在 `package()` 里做安装（照上游 `deb/build.sh` 的文件清单，落到包内 `bin/`）。

## 编译步骤

```bash
# 1. 取源：上游官方组织仓的 commit 归档（其 version 文件即 2.2.6）
#    官网 wiki.ucis.nl / oss.ucis.nl 的 https 为自签证书、http 已 503，故不使用
curl -L -o quicktun.tar.gz \
  https://github.com/UCIS/QuickTun/archive/e052c0266e655b6dc03211a93502358cd163fd6c.tar.gz

# 2. 应用补丁（两处：CC 可注入 + 硬链接兜底）
patch -p1 < patches/0001-build.sh.patch

# 3. 让编译器与依赖可见
export CC=/data/service/hnp/bin/clang
export CPATH=<libsodium>/include          # build.sh 用 #include <sodium/...> 探测
export LIBRARY_PATH=<libsodium>/lib       # build.sh 用 -lsodium 探测

# 4. 构建（唯一入口；脚本自身 set -e，失败即退出）
sh build.sh          # 输出应含 "Using shared libsodium."

# 5. 产物
ls out/              # quicktun quicktun.{raw,nacl0,nacltai,salty,keypair}
```

## 适配要点

| # | 问题 | 处理 |
|---|------|------|
| 1 | `build.sh` 把编译器写死为 `cc="cc"`，而 OHOS 工具链 PATH 里**不存在 `cc`** | 补丁改为 `cc="${CC:-cc}"`；`CC` 由 Conan 的 `AutotoolsToolchain` 注入（R33，不裸用 shell 变量） |
| 2 | `ln out/quicktun.combined out/quicktun` 用硬链接产出主程序名，HMDFS 上硬链接被拒（`Operation not permitted`，实测两次 inode 不同 ⇒ 走的是 cp 分支） | 同一补丁加 `|| cp` 兜底，产出物内容不变 |
| 3 | `build.sh` 只靠"编译器能否 `-lsodium` 链上"来选后端，且**探测失败会静默改用仓库自带的 TweetNaCl 并照常产出二进制** | 配方 `build()` 之后断言后端确为 libsodium：`obj/tweetnacl.o` 不得存在 + 产物内须有 libsodium 专有符号 `crypto_generichash_blake2b`。这是防止"声明依赖却没真用上"的硬闸 |
| 4 | `LIBRARY_PATH="/usr/local/lib/"` 被写死进脚本（烧死系统路径） | 不改动：它只是**追加**在 LIBRARY_PATH 末尾，配方把 libsodium 路径 `append_path` 到前面即可命中，无需碰这个字面量（避开 R49/PF6 的共享前缀注入） |
| 5 | 上游 tarball 内没有 LICENSE 文件（BSD-2-Clause 全文只在各 `.c` 头部注释里） | `license = "BSD-2-Clause"` 照源码头注释判定；`package()` 不伪造 `licenses/` 文件，此点在 notes.md 中披露 |

## 运行期能力（HarmonyOS PC 实测）

> 口径：逐号探、报 errno 前先贴调用原样；"节点不存在"与"节点存在但 EACCES"分开写。

| 能力 | 调用原样 | 实测读数 | 影响 |
|------|----------|----------|------|
| TUN 节点 | `open("/dev/net/tun", O_RDWR)`（common.c:231） | 失败 **EACCES(13)**；对 `/dev/net`、`/dev/net/tun` 的 `stat` 与 `open` 一律 EACCES，且同目录下必然不存在的设备名同样返回 EACCES ⇒ **节点存在性不可证**，不作「存在/不存在」任一定性（见版本级 notes.md 探针矩阵、manifest.yaml） | 守护进程主路径不可运行 |
| TUN 配置 | `ioctl(fd, TUNSETIFF, &ifr)`（common.c:235） | 未达：前一步 open 已失败 | 同上 |
| 地址解析 | `getaddrinfo(host, NULL, NULL, &ai)`（common.c:171/177） | 见 notes.md 探针矩阵 | 可用 |
| 事件循环 | `poll(fds, 2, timeout)`（common.c:353；**上游用的是 poll，不是 ppoll**） | 见 notes.md 探针矩阵 | 可用 |
| 降权 | `chroot(dir)` / `setgid()` / `setuid()`（common.c:293/298/299） | 见 notes.md 探针矩阵 | 需特权启动 |
| 密钥派生 | `quicktun.keypair -i <hex> -o space` | ✅ 可用，输出与 libsodium `crypto_scalarmult_base()` 逐字节一致 | 消费者测试面 |

注：台账把机制写成 `mknod_chroot` / `ppoll_timing` / `setuid_cap`，**复验后其中三项与源码不符**
（详见版本级 `notes.md`）：全仓无 `mknod()`、无 `ppoll()`（是 `poll()`）、无 capabilities/prctl
（只有 `setuid/setgid/chroot`）。

## 测试

上游**没有任何自动化测试套件**（无 Makefile/ctest/meson，`build.sh` 无测试步骤，
`src/` 下无测试源文件）。测试面是 `test_package/test_quicktun.c`：以使用者身份调用随包
发布的 `quicktun.keypair`，并在进程内用 libsodium 独立算出同一秘密标量的 Curve25519
公钥作预言机逐条断言。断言总数与实际通过数以运行时自报行为准，见版本级 notes.md 的五维账本。

## 交付物

`archives/q/quicktun/2.2.6/`：`conanfile.py`、`conandata.yml`、`patches/0001-build.sh.patch`、
`test_package/`（`conanfile.py` + `CMakeLists.txt` + `test_quicktun.c` + `MANIFEST.yml`）、
`manifest.yaml`、`notes.md`。
