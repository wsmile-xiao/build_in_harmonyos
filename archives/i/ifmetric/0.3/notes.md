# ifmetric 0.3 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-09-24
- 编译器: clang/clang++ 15（OHOS 工具链，libc++ 17，Release，arch armv8）
- 状态: built

## 编译步骤

1. `source()`：解压官方 tarball 后，按 E490/E543 对已知 autotools helper
   （`configure`、`config.guess`、`config.sub`、`install-sh`、`missing`、`mkinstalldirs`）
   逐个补回执行位（HMDFS 默认 660 会丢掉 tar 里的 mode；**不做 `chmod -R +x`**）。
2. `generate()`：`AutotoolsToolchain` 追加
   `--build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-ohos`
   （上游 configure 出自 2004 年左右的 autoconf，其 `config.sub` 无法规范化
   aarch64 OHOS 三元组，必须两侧都显式给出），
   以及 `--disable-lynx --disable-xmltoman`（见下"遇到的问题 #1"）。
3. `build()`：`apply_conandata_patches`（0001/0002）→ 把 `configure` 里的
   `umask 077` 放宽为 `umask 022`（E011/E114）→ `autotools.configure()`
   → `autotools.make(args=["-j1"])`（E074：HMDFS 建不出 jobserver FIFO）。
4. `package()`：`Autotools.install()` + 把 `LICENSE` 拷进 `<pkg>/licenses/`。

完整 configure 命令（由 AutotoolsToolchain 生成）：

```bash
./configure --prefix=... --bindir=... --sbindir=... --libdir=... \
  --build=aarch64-unknown-linux-gnu \
  --host=aarch64-unknown-linux-ohos \
  --disable-lynx --disable-xmltoman
make -j1
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 末尾硬失败：`configure: error: *** Sorry, you have to install lynx or use --disable-lynx ***` | 上游把文档生成工具 lynx 当成 `AC_MSG_ERROR` 级必需项（`have_lynx=no` 即中止），与被编译的二进制毫无关系 | 加 `--disable-lynx`。同族的 `xmltoman`（管 man page 重建）只是 WARNING 级软降级，一并加 `--disable-xmltoman` 以免依赖宿主 perl 工具链 |
| 2 | `config.status` 全线 `Permission denied`，Makefile 没生成，`make` 报 `No targets specified and no makefile found` | E011/E114：configure 生成的 config.status 用 `(umask 077 && mktemp -d "./confstatXXXXXX")` 建临时目录，HMDFS 强制 setgid → `drwx--S---`，连属主自己都不可以写 | `build()` 内把 `configure` 的 `umask 077` 替换为 `umask 022`（保留真实临时目录创建，非绕过）；先例 archives/i/iec16022/0.3.1 patches/0003 |
| 3 | 解包后脚本无执行位，`sh configure` 之外形态的调用报 Permission denied | E490/E543：HMDFS 上 conan 解包落盘默认 mode 660 | `source()` 内只对已知 autotools helper 名单逐个 `chmod +x`，遵守 E490 的 `forbid: chmod -R +x` |
| 4 | **编译产物能跑但每次调用都失败**：`NETLINK: Packet too small or truncated! 728!=16!=1340`（`socket`/`bind`/`send` 均无报错） | 上游 `netlink_request()` 用栈上 `char replybuf[2048]` 收 netlink 数据报。本机 RTM_GETLINK dump 实测 **19276B / 14 条**，其中华为无线类接口（Hisilicon0/wlan0/wlan1/p2p0/chba0/nan0/ancowlan0）单条 `RTM_NEWLINK` 携带约 **1340B** 的 802.11 `IFLA_*` 属性；netlink 是数据报语义，缓冲不足时 `recv()` **静默截断**并返回满长度，随后的 `NLMSG_NEXT` 走到半截头部（`nlmsg_len`=1340 > 剩余 728）→ 自检失败退出。因为 `getifn()` 是 ifmetric 的**第一个**动作，症状形似"OHOS 不支持 netlink"，**实际不是** | `patches/0001-netlink-dump-datagram-buf.patch`：先 `recv(s, &probe, sizeof(probe), MSG_PEEK | MSG_TRUNC)`（`probe` 是单个 `char`，即 1 字节探针）拿到数据报**真实长度**（MSG_PEEK 保证不出队），再按该长度 `malloc` 后完整收取。**注意不能**直接在收数据的 `recv()` 上加 `MSG_TRUNC` 再重试——数据报已被消费，重试读到的是下一个，会静默丢消息。本条已抽成知识草稿 DRAFT-ifmetric-0.3-netlink-dump-replybuf-truncation |
| 5 | Python 侧只读探针 `bind()` 报 `OSError('bind(): bad family')` 且 `errno=None` | 设备 CPython 构建**未导出** `AF_NETLINK`/`PF_NETLINK` 常量，`socket.bind()` 的 family 分支里没有该 case——是**解释器构建限制**，不是内核拒绝（同一进程 `socket(16,3,0)` 成功返回 fd=4 即证内核可用） | 只读面判定改由**编译产物**做（见"验证命令"第 4/5 条），不采信 Python 侧结论 |
| 6 | **真机全绿、CI 独红**：CI 首错 `linux/socket.h:23:8: error: redefinition of 'sockaddr_storage'` + `sys/socket.h:377:8: note: previous definition is here`（buildbot #59586，落在 `构建测试完成`），本机同版本 `conan create` 却从未报过 | OHOS sysroot 的 **musl `sys/socket.h` 把 `struct sockaddr_storage` 包在 `#ifndef __MUSL__` 里**（实测该文件 370-384 行），而内核 UAPI `linux/socket.h:23` 是**裸定义**；设备上 `~/usr/local/bin/clang` 是 wrapper，恒定注入 `-D__MUSL__`（实测 `cat` 该 188 字节脚本），于是本机走的是"musl 让位、只留 UAPI 定义"这条路；CI 用裸 clang，两份定义同时出现 ⇒ `ifmetric.c` 的 `sys/socket.h`(第5行) + `linux/if.h`(第7行，它又 include `linux/socket.h`) 必冲突。**同一份 sysroot 头文件、同一版本 clang，差异只在有无 `-D__MUSL__`** | 复用 **E091（define-guard）**：`patches/0002-ohos-uapi-sockaddr-storage-guard.patch` 在 `ifmetric.c` 与 `nlrequest.h` 的 UAPI include 前后加 `#ifdef __OHOS__ / #define sockaddr_storage __linux_sockaddr_storage / #endif`（收尾 `#undef`），`__OHOS__` 实测由 clang 对 `aarch64-unknown-linux-ohos` 三元组预定义 ⇒ 非 OHOS 平台零影响。**不改 libc 头、不注入全局 `-D__MUSL__`**（后者会连带改变 musl 头语义，属掩盖而非修复） |

### 问题 #6 的双侧验证证据（CIW 2026-09-24，设备 `~/tmp/uc2/hw-1-CIW/ifmetric-fix/`）

用 `clang-15`（wrapper 的**真身**，不经 `-D__MUSL__`）+ `--sysroot=$HOME/usr/local/sysroot` 复刻 CI 的编译条件：

| 实验 | 命令要点 | 结果 |
|---|---|---|
| 反证（未修版 + 无 `-D__MUSL__`） | `clang-15 --target=aarch64-unknown-linux-ohos --sysroot=... -I. -c ifmetric.c` | `linux/socket.h:23:8: error: redefinition of 'sockaddr_storage'` / `sys/socket.h:377:8: note: previous definition is here` —— **与 CI 日志逐字同签名同行号** |
| 修后 + CI 等价条件 | 同上，源文件为打过 0002 的版本 | `ifmetric.c` / `nlrequest.c` / `getifn.c` 三个 TU 均无 error |
| 修后 + 本机常规条件 | `clang`（wrapper，带 `-D__MUSL__`） | 三个 TU 均无 error ⇒ 补丁对既有本机路径零回归 |
| 宏可得性探针 | `printf '#ifdef __OHOS__\n#error OHOS_DEFINED\n#endif'` 编译 | 报出 `OHOS_DEFINED` ⇒ `__OHOS__` 确为该三元组的预定义宏，守卫在 CI 上会生效 |

## 上游测试情况（§10 口径，四套数字分开）

- **静态声明总数 = 0**：源码树 33 个文件内无 `tests/` 目录；顶层 `Makefile.am` 只有
  `SUBDIRS = src man doc` 与 `EXTRA_DIST`；`src/Makefile.am` 只有
  `sbin_PROGRAMS = ifmetric` + 5 个 `SOURCES`；全树无 `TESTS`、无 `check_PROGRAMS`、
  无自定义 `check:` 目标。
- **官方套件实际执行数 = 0**：不存在可执行的上游测试入口，
  **未运行 `make check`，也不声称运行过**。
- **条件/依赖/资源未执行或跳过数 = 0**（无此项可跳过）。
- **新增消费者测试 = 1 个程序（`test_package/smoke.sh`）/ 6 条断言**，
  实际执行 6/6 通过、skipped=0。消费者测试计入"适配后"合计，**不计入上游合计**。

审计细节与逐条证据见 `test_package/MANIFEST.yml` 的 `upstream_test_audit`。

## 关于特权与测试安全边界

ifmetric 的正常功能（改路由 metric）需要 `CAP_NET_ADMIN`：`go()` 对每条匹配的
main 表路由做 `RTM_DELROUTE` 后再 `RTM_NEWROUTE|NLM_F_CREATE` 重新下发。
因此消费者测试**绝不**用带路由的真实接口名调用它（会改活路由，本机与他人会话共享）。
测试采用两条零副作用路径：

1. 不存在的接口名 → `getifn()` 走完 socket→bind→send→recv→RTA 遍历后打印
   `Interface 'hw2nosuchif0' not existent.` 并退出 1 —— 证明只读面可用且不触碰写路径；
2. "存在但 main 表无路由"的真实接口（由 `/proc/net/dev` 减去 `/proc/net/route` 求得，
   本机为 `lo`）→ 枚举完成、匹配 0 条、退出 0，同样不产生任何写操作。

并用 `diff` 断言调用前后 `/proc/net/route` **逐字节一致**，把"零改链"做成硬检查。

**本包未在任何特权分支上声明通过**：无 CAP_NET_ADMIN 时的写路径行为未被断言，
`MANIFEST.yml` 的 `privilege_required_for_test: false` 与 `privilege_note` 同源说明这一点。

## 依赖版本

无外部依赖（`dependencies: []`）。仅使用 OHOS 工具链与 libc 头文件里的
`linux/netlink.h`、`linux/rtnetlink.h`。

## 验证命令

```bash
# 环境：TARGET_REPO=~/qzy/hw-2-ifmetric-0.3
#       CONAN_HOME=~/tmp/ch/home-hw-2-ifmetric
#       OHC_PROJECT_DIR=~/tmp/hw-2-shadow（设备适配版 profile 的影子工程）
export PATH=$HOME/usr/local/bin:$HOME/.harmonybrew/bin:/bin:/usr/sbin:/usr/bin:$PATH
export SSL_CERT_FILE=$HOME/usr/local/ssl/cert.pem TMPDIR=$HOME/tmp

python3 scripts/ohc-run.py conan-verify ifmetric 0.3     # G0/G1/G2/G3/G4 全 PASS
python3 scripts/ohc-run.py finish ifmetric 0.3 built
```

`conan-verify` 结果（2026-09-24 真机）：

```text
G1: PASS   G0: PASS   G2: PASS   G3: PASS   G4: PASS
✅ 配方验证通过: ifmetric 0.3
```

`test_package` 消费者测试（`smoke.sh`，conan create 的 test 阶段真实执行）：

```text
ok - packaged binary exists and is executable
ok - bare invocation prints usage and exits 0 (argc<=1 branch)
ok - --help prints usage and exits 0 without touching netlink
ok - netlink read path works end to end (RTM_GETLINK answered; absent iface -> rc=1)
ok - getifn() resolved real iface 'lo' and RTM_GETROUTE enumeration completed (rc=0)
ok - main routing table byte-identical before/after (no route was mutated)
CONSUMER_RESULT 6/6 (skipped=0)
```

只读探针实测数据（用于支撑"问题 #4"的根因，非交付测试）：

```text
type=18  buflen=  2048 recv_total= 14356 msgs=  7 truncated_datagrams=7
type=18  buflen= 65536 recv_total= 19276 msgs= 14 truncated_datagrams=0
type=26  buflen=  2048 recv_total=  1708 msgs= 22 truncated_datagrams=0
```

## 产物

| 产物 | 说明 |
|------|------|
| `bin/ifmetric` | 唯一可执行文件；上游装入 `$(sbindir)`，Conan 的 AutotoolsToolchain 指向 `<pkg>/bin` |
| `man/man8/ifmetric.8` | 上游 `make install` 的手册页（`--disable-lynx --disable-xmltoman` 只关掉 HTML/PDF 文档生成，man 页照常安装） |
| `licenses/LICENSE` | GPL-2.0-or-later 全文 |

交付目录实测共 3 个交付文件（`find <package_folder> -mindepth 1 -type f`：`bin/ifmetric`、`man/man8/ifmetric.8`、`licenses/LICENSE`），另有 conan 自带的 `conaninfo.txt`/`conanmanifest.txt`。

`package_info()`：`package_type="application"`，`libs`/`includedirs`/`libdirs` 均置空，
`bindirs=["bin","sbin"]` 并对每个目录 `runenv_info.prepend_path("PATH", ...)`，
使消费者经 `VirtualRunEnv` 即可直接执行被测二进制。

## 取包与来源核验

- 真上游 = `https://0pointer.de/lennart/projects/ifmetric/`（由 Debian `.dsc` 的
  `Homepage` 字段与 PGP 签名证实，作者 Lennart Poettering）。
  SCT 早期登记的 `autistici.org/interlambda` 双端均不可达（设备 DNS 解析失败 /
  Windows 侧 TLS 握手失败），已更正。
- 官方 tarball 设备侧实测 HTTP 200、1.35s 可达；
  `sha256 = 0fa8510a4e34e555f136f9df81d26618313f2d69a4880c0fb5967f19502f1aec`（81502B）
  **即官方值**，`conandata.yml` 使用官方 URL + 官方 sha256。
- Debian `orig.tar.gz`（88fa14d1…，81896B）经 `.dsc` sha512 签名佐证与
  `diff -r` 比对，与官方包**内容逐文件相同**（33 文件，差异仅 gzip 封装），
  故**无需镜像取包、无需 E347 dlcache 预置**。

## 知识库使用记录

- 复用：E011/E114（HMDFS `umask 077` + `mktemp` 临时目录 EACCES）、
  E490/E543（autotools helper 执行位）、E074（make jobserver FIFO → `-j1`）、
  E007/E160/E122（2004 版 config.sub 无法规范化 OHOS 三元组 → 显式 `--build/--host`）、
  **E091（define-guard：OHOS `linux/socket.h` 与 musl `sys/socket.h` 的 `sockaddr_storage`
  重定义，用于问题 #6 的 patches/0002）**、
  R32（`validate()` os 门）、R38（工具类 `commands.json`）。
- 新增（路径 B）：`DRAFT-ifmetric-0.3-netlink-dump-replybuf-truncation.{kv,md}`
  —— 遗留 netlink 工具固定小 replybuf 在 HarmonyOS PC 大 IFLA 属性接口下被静默截断，
  修法为 `MSG_PEEK|MSG_TRUNC` 两步取值。`draft-review` 质量预检三项全绿，
  最高相似度仅 E334=0.11，预审建议 create。
- 明确**未采用** M13（`DRAFT-PKG-VER-makefile-install-cmd-absent-makevar-override`）：
  该草稿自己的 `safety_boundary` 即写明"不适用 autotools 项目"，而 ifmetric 是
  autotools 且自带 `install-sh`，实测 `/bin/install` 亦存在 ⇒ 按 §6.2⑦3"禁止空走"不派发。
- netlink 既有命中 2 条经逐条比对**不构成 hit**：E091 是编译期
  `sockaddr_storage` 重定义（`#define` 改名守卫），E237 是内核缺
  `NETLINK_GENERIC`/`/proc/acpi`（运行期降级）——签名与解法均与本条不同。
---

**编译结束**: 2026-09-24 16:29
**最终状态**: built
