# quicktun 2.2.6 适配笔记

## 编译环境

- 构建系统: **custom** —— 上游唯一构建入口是仓库根的 `build.sh`（90 行裸 shell），
  无 configure / Makefile / CMakeLists / meson.build，也没有任何 install 目标。
  配方侧只用 Conan `AutotoolsToolchain` 产出 CC/CFLAGS/LDFLAGS 环境，实际编译是
  `sh build.sh`（不依赖执行位与 shebang）。
- 编译日期: 2026-09-25（本轮 W3 重跑 19:17–19:18，设备本地时间）
- 编译器: OHOS clang 15.0.4（aarch64-linux-ohos），profile `ohos-aarch64`
- Conan 参考: `quicktun/2.2.6@ohpcd/stable`
- 构建主机: 鸿蒙 PC B 机（HarmonyOS aarch64），worktree `feat/quicktun-2.2.6`
- 状态: built

## 复跑说明（第 1 棒那轮 W3 证据为什么作废）

**提交态的 `conandata.yml` 里带着一行镜像前缀。** 第 1 棒留下的 HEAD 版本把
`sources.url` 写成**两项列表**，首项是 `gh-proxy.com/…`、第二项才是官方原址。
本仓硬闸 PF7 源 URL 闸（R39；`scripts/ohc/preflight.py:356-382`，
`_PF7_MIRROR_HOSTS` 明确含 `gh-proxy.com`）对它的判决语原文：

```
PF7 源URL闸(R39): archives/q/quicktun/2.2.6/conandata.yml:12 镜像前缀 gh-proxy.com
（CI 自动加镜像回退，手写即 R39 违规 579 例）——conandata 只写上游官方源 URL，
镜像回退由 CI 自动处理
```

**来源不是"有人要写镜像"，而是框架回写被顺手提交**（本轮实测坐实）：
`ci/conan/build_and_test.sh:1026-1029` 的 Mirror fallback 会把 `github.com` 的单值
`url:` 改写成"镜像 + 原址"列表，并留一个 `${CONANDATA}.orig` 备份（包目录里那个
`conandata.yml.orig` 就是它的产物）；pre-download 的还原 trap（`:1179-1188`）
**备份发生在改写之后**，只回滚 `file://` 替换、不回滚这一步 ⇒ 每跑一次 W3，盘上
必然留下那两行镜像。无论来源如何，**提交态带镜像就是 R39 硬违规**（CI 自己会加
回退），已改回单条官方原址。

改完后 PF7 实跑读数 **1 条 → 0 条**：同一个闸函数 `check_source_urls()` 分别对
旧/新两版文件各跑一次，旧版复现上面那条原文、新版 `FINDINGS 0`。
（旁证一条：`_PF7_DEBIAN_HOSTS`（`preflight.py:361-362`）加 `+dfsg` 判"Debian 下游
重打包源"（`:379-381`）⇒ 上游那份 `.orig` 也**不能**当 conandata 源，
所以取源只能落在官方组织仓归档上。）

`conandata.yml` 属导出件 ⇒ recipe revision 变更 ⇒ 第 1 棒的 conan-verify / W3 /
finish 证据一律作废，按新 HEAD 重跑。重跑后三件报告的哈希都变了（可反证"没拿旧日志充数"）：

| 报告 | 上一轮 md5 | 本轮 md5 |
|------|-----------|----------|
| `reports/conan-create.log` | `b77d4a33bd22e473f9df4995d4d4848d` | `3b1b2b782d7045de1e6b15d3c354d166` |
| `reports/conan-verify-report.md` | `8042a5ae10185a27c38695b7fb7e5690` | `6063649eaa9936a6c5342784afaa5a79` |
| `reports/w3-local-ci.log` | `77a230a6ff08e86d95ebd4194ece9d85` | `687535e604f1481a93308d73b8c14b63` |

`.ci-result.json` 同源更新：`timestamp` 18:58:02 → **19:18:15**，
`integrity_hash` `c408097a39e3a6b3` → **`9b046a9c433f366e`**，
`log_sha256` `64f35f489448a2fd…` → **`33e1d74274f1e71a…`**，`exit_code: 0`。
判决文字：`finish3.log:86` `✅ W3 本地 CI 模拟通过` +
`reports/w3-local-ci.log:284` `VERDICT: PASS`（该文件 `❌`/`FAIL` 计数均为 0）。
`finish3.log:131` 的 `失败步骤: step5b, step8` 属 finish 侧已知框架互斥面
（step8 = `gen_summary 失败: 'str' object has no attribute 'append'`，
`finish3.log:120`），**不作为 W3 判据**。

> ⚠ 本轮重跑后 `conandata.yml` 又被框架改回那两行镜像列表（工作树 `M` 态）⇒
> **建 PR 前必须 `git show HEAD:archives/q/quicktun/2.2.6/conandata.yml` 还原**，
> 仓内与 PR 里都不得留那两行。

## 取源（本轮实测对字）

上游官网 `wiki.ucis.nl` 与其对象存储下载区 https 为自签证书、http 已 503，官方
`.orig` 无法作为 conandata 源（本仓把 Debian 下游重打包域名单独列为违规源，
`_PF7_DEBIAN_HOSTS`）。取源改用**上游项目自有官方组织仓** UCIS/QuickTun 的
master 末次提交归档。实测命令与读数（B 机，2026-09-25 19:1x）：

```bash
curl -sSL -o qt226-gh-b2.tar.gz -w "code=%{http_code} bytes=%{size_download}\n" \
  https://github.com/UCIS/QuickTun/archive/e052c0266e655b6dc03211a93502358cd163fd6c.tar.gz
# code=200 bytes=22459     rc=0
sha256sum qt226-gh-b2.tar.gz
# 26b7b8f396e0a3c6012adfe782bceec34906545fa32d132042949518f7bb0ac2  qt226-gh-b2.tar.gz
```

⇒ `conandata.yml` 的 `sha256` = **归档文件自身的哈希**，与实测逐字相同（不是源码
聚合哈希；上一版注释把两件事写在同一段里，读起来像在描述 `sha256` 字段，已改写澄清）。

与上游发布物 `quicktun_2.2.6.orig.tar.gz` 的等价性（一手清点，
`~/tmp/uc2/z45-quicktun/src-verify.log`）：

| 项 | 组织仓 commit 归档 | 上游 `.orig` |
|----|-------------------|--------------|
| HTTP / 字节 | 200 / 22459 | 200 / 22750 |
| 归档 sha256 | `26b7b8f396e0a3c6012adfe782bceec34906545fa32d132042949518f7bb0ac2` | `f2d27a06fba6eb38db9642a0372dca1cb6c8fb3740e13e83ff4ee06a21d5634a` |
| `version` 文件内容 | 2.2.6 | 2.2.6 |
| `src/` 下 .c/.h 聚合 sha256 | `566a184c98c6f024981abcb97bef4d91209b033547e414c6538eb185cc613602` | 同一个值（逐字节相同） |
| 文件数 | 23 | 22 |
| 整树逐文件 diff | 多一个 `.gitignore`；`build.sh` 差上游自身的一个参数顺序修复提交 | — |

## 编译步骤

1. `source()`：`get(self, **self.conan_data["sources"], strip_root=True)` 拉取上面的官方归档。
2. `build()` 首步 `apply_conandata_patches()` 打 `patches/0001-build.sh.patch`（两处，见下节）。
3. `generate()`：`AutotoolsToolchain` 产出 CC/CFLAGS/LDFLAGS；再用 `Environment` 把
   **libsodium 自己的 `package_folder`** 下的 includedirs/libdirs 追加进
   `CPATH`/`LIBRARY_PATH`（R49：不引用任何共享系统前缀）——上游脚本没有
   `--with-sodium` 之类开关，只认这两个编译器环境变量。
4. `build()`：`sh build.sh` → 立刻 `_assert_libsodium_backend()`（见问题 #3）。
5. `package()`：上游无 install 目标，按 `deb/build.sh` 的安装面把 `quicktun` 与
   `quicktun.*` 各协议变体收进包内 `bin/`。
6. `conan-verify` → `finish quicktun 2.2.6 built`（内含 W3 本地 CI 模拟）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `build.sh[58]: cc: inaccessible or not found`（原样构建直接失败，`~/tmp/uc2/z45-quicktun/build-asis.log:5`） | `build.sh:5` 把编译器写死成 `cc="cc"`，OHOS 工具链里没有 `cc` 这个别名，脚本也没有任何可覆盖入口（不是 make、不是 configure） | 0001 补丁改成 `cc="${CC:-cc}"`，CC 由 Conan `AutotoolsToolchain` 注入（R33：编译器一律来自 Conan conf）。同族先例：`knowledge/drafts/DRAFT-9848-qbe-device-e2e-runtime-evidence.md:58`、池草稿 M18 `DRAFT-PKG-VER-suckless-baked-paths-makevar-override` |
| 2 | HMDFS 上 `ln out/quicktun.combined out/quicktun` 报 `Operation not permitted` | 知识条目 **E079**：`$HOME` 挂 HMDFS，分布式架构不支持硬链接 | 同补丁加 `2>/dev/null || cp` 兜底 —— 即 E079 推荐方案本身（`knowledge/doc/E079.md:20-22` 方法 `command-substitute`「将硬链接操作替换为复制（cp）」）。产物侧证据：`out/quicktun` 与 `out/quicktun.combined` **inode 不同**（`2305843009229931423` vs `2305843009229931067`，`~/tmp/uc2/z45-quicktun/artifact-probe.log:2-3`）⇒ 走的是 cp 分支 |
| 3 | **声明依赖 libsodium、实际却可能交付内置 TweetNaCl 的二进制，而退出码仍是 0** | `build.sh:37` 只用 `$cc -shared -lsodium tmp/libtest1.c` 探测后端；探测失败就走 `else`（`build.sh:49-58`）编译仓库自带 `src/tweetnacl.c`、把 `CRYPTLIB` 换成 `obj/tweetnacl.o`，**照常产出全部 out/ 二进制**。原样构建实跑到该分支（`build-asis.log:2-4` 打出 `Building TweetNaCl...`） | `build()` 之后做**链接期产物双断言**（`conanfile.py:96-121`）：① `obj/tweetnacl.o` 出现即 `ConanException`（该目标文件只有 TweetNaCl 分支才编，`build.sh:52`）；② `out/quicktun.combined` 里必须含 `crypto_generichash_blake2b` —— 实测该符号**在上游整棵源码树里出现 0 次**（`grep -rc crypto_generichash <src>` 无输出、`src/tweetnacl.h` 只导出 crypto_auth/box/core/hash/onetimeauth/scalarmult/secretbox/sign/stream/verify），只可能来自 libsodium。本轮实测后端归真：`reports/w3-local-ci.log:189` 打出 `Using shared libsodium.` |
| 4 | 守护进程主路径跑不起来：`Could not open tun/tap device file: Permission denied`（`artifact-probe.log:27`） | `/dev/net/tun` 相关面在本机被拒（读数见下面「能力矩阵」，定性归主理） | 测试面改走 QuickTun 里唯一**不需要 TUN、不需要 root、不需要网络**就能跑到真实加密代码的路径：`quicktun.keypair`（消费者测试 + libsodium 独立预言机交叉核对，46 条断言） |
| 5 | `make: jobserver mkfifo: /storage/Users/currentUser/tmp/GMfifo32097: Operation not permitted`（`reports/w3-local-ci.log:271`） | HMDFS/tmpfs 上 make 的 jobserver 具名管道被拒（E002/E046 同族，已知平台面） | 非阻塞：make 自动退回串行继续构建，产物与测试照常（同轮 `[100%] Built target test_quicktun`、`:283` 46/0） |

## 源码修改

| 补丁 | 位置 | 内容 |
|------|------|------|
| `patches/0001-build.sh.patch` hunk1 | `build.sh:5` | `cc="cc"` → `cc="${CC:-cc}"` |
| `patches/0001-build.sh.patch` hunk2 | `build.sh:70` | `ln out/quicktun.combined out/quicktun` → `... 2>/dev/null \|\| cp out/quicktun.combined out/quicktun` |

补丁 `patch_type: portability`；不含平台宏（无 `__OHOS__`）、不含绝对路径、不注入
编译选项，只这两处（PF5/R8 平台宏闸与共享前缀闸口径下干净）。

## 依赖版本

| 依赖 | 版本 | 说明 |
|------|------|------|
| libsodium | 1.0.22 | 唯一 `requires()`，也是 QuickTun 的加密后端；W0 侧 `preflight_check.sh` 已确认已发布，本轮 `reports/conan-create.log:56` 显示 `libsodium/1.0.22#1b4ff2170c265e2ddbc9e0fe4f9fd57a - Cache` |

上游 `build.sh:33` 自己会把 `/usr/local/lib/` 前置进 `LIBRARY_PATH`。本机实测
`/usr/local` **不存在**（`ls: /usr/local: No such file or directory`）⇒ 探测命中的
只能是通过 `Environment` 注入的 libsodium 私有 `package_folder`，不存在"链到系统库"
的污染路径。

## 能力矩阵（真机读数，逐条调用原样 + 返回值 + 对照）

来源：`~/tmp/uc2/z45-quicktun/probe_caps{,2,3}.c` 与同名 `.log`（第 1 棒三轮探针，
独立小程序、不含被测包代码；每项在 `fork()` 出的子进程里执行，故信号打死只影响该项，
实现见 `probe_caps3.c:51-65`）。整理原则：**逐号列**、报 errno 前先贴调用原样、
"节点不存在(ENOENT)"与"被拒(EACCES)"分开写。**本节只摆读数，不做"平台不支持"定性。**

### 1) TUN 设备面（上游唯一的隧道出口）

| 调用原样 | 读数 | 对照 |
|----------|------|------|
| `stat("/dev/net", &st)`（`probe_caps3.c:86`） | `rc=-1 errno=13 EACCES` | 父目录本身即被拒 |
| `stat("/dev/net/tun", &st)`（`:79`） | `rc=-1 errno=13 EACCES` | — |
| `open("/dev/net/tun", O_RDWR)`（`:92`，对应上游 `src/common.c:231`） | `fd=-1 errno=13 EACCES` | 正对照 `open("/dev/null", O_RDWR)` → `fd=3 errno=0`（`:115`）⇒ `/dev` 本身可达，问题限于 `/dev/net` |
| `open("/dev/net/tun", O_RDONLY)`（`:98`） | `fd=-1 errno=13 EACCES` | flags 反证：换 `O_RDONLY` 结果不变 ⇒ 与读写模式无关 |
| `open("/dev/net/definitely-not-a-device-zzq", O_RDWR)`（`:107`）★存在性对照 | `fd=-1 errno=13 EACCES` | **连必然不存在的名字也是 EACCES** ⇒ 本机上 EACCES 不能证明节点存在（既不能说"存在但被屏蔽"，也不能说"不存在"） |
| `ioctl(fd, TUNSETIFF, (void *)&ifr)`，`ifr.ifr_flags = IFF_TUN`（`:122-128`，对应上游 `src/common.c:235`） | **未达**（前一步 `open` 已失败） | 不下任何 TUNSETIFF 结论 |

> 编译走哪个分支是可证的，不必猜：上游把隧道出口写成
> `#if defined(__linux__)` → `open("/dev/net/tun", O_RDWR)`（`common.c:228-235`）、
> `#elif defined SOLARIS` → `/dev/tun`+`/dev/ip`（`:236-249`）、`#else` → 直接开
> `INTERFACE`/`/dev/tun0`（`:249-252`）。本包二进制的运行期报错原文是
> `Could not open tun/tap device file: Permission denied`
> （`~/tmp/uc2/z45-quicktun/artifact-probe.log:27`），逐字等于 `:231` 那条分支的措辞、
> 不等于另两条 ⇒ **实测命中 `__linux__` 分支**。（此处只摆读数，不据此对"平台是否支持"定性。）

### 2) `mknod`（上游全仓无此调用，仅为核实台账里"quicktun 需要 mknod"的口径）

| 调用原样 | 读数 | 对照 |
|----------|------|------|
| `mknod("/tmp/qt-probe-node", S_IFCHR \| 0600, makedev(1, 3))`（`probe_caps2.c` 同族行） | `rc=-1 errno=30 EROFS`（`/tmp` 只读，第 2 轮） | 该读数**只证明 `/tmp` 只读**，不证明 `mknod` 能力（第 2 轮的这一条被第 3 轮换址重做） |
| `mknod("/storage/Users/currentUser/tmp/qt-probe-node", S_IFCHR \| 0600, makedev(1, 3))`（`probe_caps3.c:258-265`，落在 HMDFS 可写区） | `rc=-1 errno=1 EPERM` | 正对照：同进程同目录下的写文件/`pipe()` 均正常 ⇒ 不是路径不可写，而是该调用被拒 |

### 3) 降权 / 特权面（上游 `src/common.c:293-299` 的 chroot+setgid+setuid 链）

| 调用原样 | 读数 | 对照 |
|----------|------|------|
| `chroot(".")`（`probe_caps3.c:232-236`，上游 `common.c:293`） | 子进程被**信号 31 SIGSYS（Bad system call）**打死，`WTERMSIG=31` | 同一夹具下其余各项正常返回 ⇒ 不是 harness 问题；SIGSYS 形态与 seccomp 按 syscall 号拦截一致 |
| `setgid(getgid())`（`:238-242`，上游 `common.c:298`） | `rc=0 errno=0` | 反证同文件 `setuid(0)`：`rc=-1 errno=1 EPERM`（`:250-254`）⇒ 同 uid 自设可、提权不可 |
| `setuid(getuid())`（`:244-248`，上游 `common.c:299`） | `rc=0 errno=0` | 同上 |
| `getpwnam("nobody")`（`:269-274`，上游降权目标查找） | 返回 `NULL`，`errno=0` | 同文件 `getpwuid(getuid())` 亦 `NULL`/`errno=0`（`:276-280`）⇒ passwd 数据库面整体为空，非本调用独有；降权路径在本机需另置 passwd 面 |

### 4) `#17` poll / ppoll（上游 `src/common.c:318/353` 的事件循环与超时）

夹具要点：**必须用"永不就绪"的 fd 才量得到真实等待**。第 2 轮把 `POLLOUT` 的写端也放进
`fds[2]`（`probe_caps2.c:205-206`），第二个 fd 永远可读/写 ⇒ `poll` 立刻返回，被误记成
"20ms/200ms 也 0ms 返回、定时坏了"（`probe-caps2.log` 带 `<<< 提前返回` 标记）。
第 3 轮换 Single fd = 未写过的 pipe 读端（`probe_caps3.c:166-179`）重做：

| 调用原样 | 读数 |
|----------|------|
| `poll(fds, 1, 1)`（`:174-186`） | `rc=0 errno=0`，实测等待 1.1ms ⇒ 超时如期生效 |
| `poll(fds, 1, 20)` | `rc=0 errno=0`，等待 20.2ms |
| `poll(fds, 1, 200)` | `rc=0 errno=0`，等待 200.3ms |
| `poll(fds, 1, -1)` + `alarm(1)`，`sigaction.sa_flags = 0`（不置 `SA_RESTART`，`:208-229`，上游默认 timeout 即 -1） | `rc=-1 errno=4 EINTR`，等待 1000ms ⇒ EINTR 语义正常、不自动重启 |
| `ppoll(fds, 1, &ts{50ms}, &mask{})`（`:190-205`，上游未用，补清单另一半） | `rc=0 errno=0`，等待 50.2ms |

### 5) `#18` getaddrinfo / 解析器（上游 `src/common.c:171/177` 传 `hints=NULL`）

| 调用原样 | 读数 |
|----------|------|
| `getaddrinfo("localhost", NULL, NULL, &res)` | `rc=0`，`ai_family=2`（AF_INET） |
| `getaddrinfo("127.0.0.1", NULL, NULL, &res)` | `rc=0`，AF_INET |
| `getaddrinfo("::1", NULL, NULL, &res)` | `rc=0`，AF_INET6（`probe-caps.log` 第 1 轮另给 `ip6-localhost` → AF_INET6） |
| `getaddrinfo("10.0.0.1", NULL, AI_NUMERICHOST, &res)` | `rc=0` |
| `getaddrinfo("no-such-host.invalid", NULL, NULL, &res)` | `rc=-3 EAI_AGAIN`（负对照：解析器会如实报错，不是恒真） |
| `getaddrinfo(NULL, "1234", {AI_PASSIVE\|SOCK_DGRAM}, &res)` | `rc=0` |
| `socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP)`（`probe_caps3.c:145-148`，上游 `common.c:187`） | `fd=3 errno=0` 成功（第 2 轮同一条曾印成 `errno=22`，是**探针读了 errno 残值**——`socket()` 成功路径不重置 errno，第 3 轮已在调用前 `errno = 0`） |
| `access("/etc/resolv.conf", R_OK)` | `rc=0 errno=0` |
| `access("/etc/nsswitch.conf", R_OK)` | `rc=-1 errno=2 ENOENT`（**节点不存在**，与上面 EACCES 分列） |

### 6) 探针自身的两轮翻案记录（留作口径，别当结论用）

- 第 1 轮 `probe_caps` 跑到 resolv 面之后**整进程** `Signal 31 (core dumped)`
  截断（`probe-caps.log` 末行）⇒ 第 2 轮起改成每项 fork 子进程隔离。
- 第 2 轮三处读数被第 3 轮否证并修正：poll 夹具用了恒就绪 fd（上文 4)、`mknod` 打在
  只读 `/tmp` 拿到 EROFS（上文 2)、`socket()` 成功却印出 `errno=22`（上文 5)。
  ⇒ 本矩阵以**第 3 轮**为准，第 1/2 轮只保留作对照与"报 errno 前先贴调用原样"的教材。

## 验证结果

```text
# —— conan create + 消费者测试（本轮 W3，同源 reports/w3-local-ci.log）——
上游 QuickTun 无任何自动化测试套件 ⇒ 上游用例数 = 0（口径与逐条清点见
  test_package/MANIFEST.yml:13,20-28；静态断言计数 46 见 :43）
新增消费者测试 test_package/test_quicktun.c：检查项 46 条，失败 0 条   (w3-local-ci.log:283)
VERDICT: PASS                                                        (w3-local-ci.log:284)
conan create passed                                                  (w3-local-ci.log:286)
L1a test_package 被 conan create 真实执行 / L1b 有执行证据            (w3-local-ci.log:288-289)
L1e 破坏性负照（把 bin/ 搬走再跑）确认测试真的依赖被测物               (w3-local-ci.log:294-296)
L2 烟雾：quicktun / .combined / .keypair / .nacl0 / .nacltai / .raw / .salty
   七个二进制的 --version 全 OK                                        (w3-local-ci.log:298-304,308)
L0/L1_RESULT=pass，L5 bin/ 有内容                                      (w3-local-ci.log:39,293,306-307)

# —— conan-verify（reports/conan-verify-report.md）——
**Verdict**: PASS                                                     (conan-verify-report.md:3)
G0/G1/G2/G3/G4 ✅ PASS；L2/L4/L5 ✅ PASS                              (conan-verify-report.md:8-49)
```

> **对上面这份 verify 报告的诚实注解**（别让 ✅ 冒充覆盖）：
> `G4` 那行带 `⚠️ 无法找到程序包 ID`（`:40`）；`L2/L4/L5` 三条虽然标题是
> `✅ PASS`，正文写的是 `⏭️ 跳过（无 cache 路径）`（`:42-49`）——真正的
> L2/L4/L5 读数出自 W3 本地 CI 那一侧（`w3-local-ci.log:291-308`）。
> `G0` 报 `Knowledge hit: E490`（`:9`）不适用本包：E490 讲 autotools helper 脚本
> 执行位，而 QuickTun 树内根本没有 `configure`/`config.guess`/`install-sh`
> （上游 23 个文件的实测清单见 `~/tmp/uc2/z45-quicktun/l-gh.txt`——该文件实测 23 行，
> 行数与文件数一致、未见额外条目），配方也是 `sh build.sh`
> 显式调用、不依赖执行位。

## 未覆盖面（照实披露，不含定性）

1. **守护进程主路径未运行过**：`quicktun`/`quicktun.combined` 的隧道建立需要打开
   `/dev/net/tun`，本机该项读数为 EACCES（能力矩阵 1) ⇒ 建隧、加解密报文转发、
   `poll` 事件循环在真实隧道流量下、`chroot`+`setgid`+`setuid` 降权链
   （`common.c:293-299`）**均未被端到端验证**。上面 L2 的七个 `--version` 只证明
   二进制可执行并自报版本。
2. **消费者测试面**：46 条断言全部落在 `quicktun.keypair`（-v 版本面、`-o space/human/bin`
   三种输出、同输入确定性、随机模式非常量、非法入参定向拒绝）。其余协议变体
   （`raw/nacl0/nacltai/salty`）只做了 `--version` 烟雾，未做数据面断言。
3. **后端归真的断言面**：`test_quicktun.c:14-16` 已写明——Curve25519 公钥比对
   **不能**区分 libsodium 与内置 TweetNaCl（同原语、同结果）；后端归由
   `conanfile.py` 的链接期双断言把住，不在测试包里。
4. **deb 分支未构建**：`build.sh:79` 的 `if [ -f /etc/network/interfaces -o "$1" = "debian" ]`
   分支未触发（本机无 `/etc/network/interfaces`，配方也只传裸 `sh build.sh`）。
5. **随机源质量**：只断言两次随机密钥不相同（C3），未做统计检验。

## 路径 B 声明

- **适配路径**：B（配方 + 知识库扩展）
- **使用知识库**：E079（HMDFS 禁硬链接 → `command-substitute`：硬链接换成 cp，
  `knowledge/doc/E079.md:11,20-22`）；E002/E046 族（`/tmp` 只读、HMDFS 模式归一，
  解释 make jobserver mkfifo 与 `mknod /tmp` 的 EROFS）；E490 由 G0 报命中但**不适用**
  （本包无 autotools helper 脚本，见上一节注解）。
- **知识库扩展**：本 PR 新增草稿
  `knowledge/drafts/DRAFT-quicktun-2.2.6-bare-script-silent-backend-swap.{kv,md}`
  ——「裸 shell 构建入口的可选后端探测失败会**静默换成内置实现**且退出码 0；
  无 configure 摘要 / 无编译命令行 / 无 DT_NEEDED 可查时，唯一硬判据是链接期产物双断言」。
  判重结论 `create`，四范围计数与逐条层次差见
  `reports/knowledge-candidate-ledger.md`。
- **关联 Issue**：#3412 https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/issues/3412（标题「【知识库扩展】quicktun 2.2.6：裸shell构建入口的编译器探测即选型失败时静默换成内置实现且退出码0」）
- **B判定**=create（一 PR 只占一个知识位：`烧死编译器`面按 hit 引用
  `DRAFT-9848-qbe-device-e2e-runtime-evidence.md:58`，`TUN 能力面`按 hit 引用
  `knowledge/drafts/E2164-draft-ocserv-vpn-tun-boundary.md:16-21`，
  `取源面`不占位、只记台账候补，理由同见台账）

## 交付物

| 文件 | 说明 |
|------|------|
| `bin/quicktun` | 组合协议主程序（`quicktun.combined` 的 cp 产物） |
| `bin/quicktun.combined` | 同上原件 |
| `bin/quicktun.raw` / `.nacl0` / `.nacltai` / `.salty` | 单协议变体 |
| `bin/quicktun.keypair` | Curve25519 密钥生成工具（消费者测试入口） |
| `reports/conan-create.log` | conan create 全链（含 `检查项 46 条，失败 0 条`） |
| `reports/conan-verify-report.md` | G0–G4 / L2 / L4 / L5 判决 |
| `reports/w3-local-ci.log` | W3 本地 CI 模拟（L0/L1/L1e/L2/L4/L5 + `VERDICT: PASS`） |
| `reports/knowledge-candidate-ledger.md` | B 判定四范围查重台账 |

上游 tarball 内**没有 LICENSE 文件**（BSD-2-Clause 全文只写在各个 `.c` 文件头
注释里），所以 `package()` 不复制 `licenses/` —— 如实披露，不伪造文件。

## 对话记录

（框架约定，`scripts/ohc/finalize_archive.py:138` 认 `### 对话 #`；本轮之前的
`finish3.log:94` 仍在报 `notes.md 无对话记录`，本节即为其补齐）

### 对话 #1 [2026-09-25]（第 1 棒：探路）

- 问题: `ohc-run.py init-build` 下来只有骨架——日志显示
  `嵌套源码检测: 未在 ... 找到构建文件`、`conandata.yml 模板不可用，跳过`、
  `conanfile.py 模板不可用（autotools），跳过`、`test_package 模板不可用，跳过`
  （`~/tmp/uc2/z45-quicktun/init-build.log`），同轮还踩到框架缺陷
  `check_env.py:33` 的 `str(e)` 未绑定 ⇒ 抛 `FileNotFoundError: .../automake`
- 操作: 按 `build.sh` 全文（90 行）手写配方与消费者测试；`recipe-search` 语料
  6173 条**无相似配方**（`recipe-search.log`）；`lang-preflight` 判定
  `task=c, detected=c`（`source_stats: c:9, bash:3，主体占比 100%`，语言例外不成立）
- 结果: 骨架期环境读数是后面所有问题的源头——同一份日志里
  `✅ clang: 15.0.4` 与 `⚠️ cc: 未找到` 并排出现（问题 #1）

### 对话 #2 [2026-09-25]（第 1 棒：W0 依赖与取源）

- 问题: 精确依赖 `libsodium/1.0.22` 是否已发布？官网下载区不可用怎么取源？
- 操作: 不使用 `preflight_check.sh` 的"无依赖声明"结论（它在 conanfile 生成前跑的，
  `preflight.log` 原文 `未找到依赖声明`），改用两条直接实证：
  `conan download libsodium/1.0.22 -r=ohpcd --only-recipe` 出现
  `Downloading recipe ...` 且 rc=0；`conan install --requires=libsodium/1.0.22
  --build=never -pr:a=ohos-aarch64` INSTALL_RC=0 并真从 ohpcd 下到二进制
  （`w0-v2-full.log`，同轮对照跑了 1.0.20）；取源侧对三个候选源逐文件比对
  （`src-verify.log`、`l-gh.txt`、`l-orig.txt`）
- 结果: 依赖发布态成立；取源定为上游官方组织仓 commit 归档，Debian `.orig` 只作
  等价性对照物、不当 conandata 源（PF7 判"Debian 下游重打包源"）

### 对话 #3 [2026-09-25]（第 1 棒：三个构建期问题）

- 问题: 原样 `sh build.sh` 失败并**已经**选了内置 TweetNaCl（`build-asis.log`）
- 操作: 定位到 `build.sh:5` 写死 `cc="cc"`、`:37` 的 `-lsodium` 链接探测失败即走
  `:49-58` else 分支、`:70` 的 `ln` 在 HMDFS 上 EPERM；一个补丁解决前两处，
  `build()` 后加链接期双断言兜住第三处；用 `Environment` 注入 `CPATH`/`LIBRARY_PATH`
- 结果: `build-fix1.log` 转为 `Using shared libsodium.`；
  补丁经 `refresh-patch --auto` 重生成为 `0001-build.sh.patch (+2/-2)`；
  inode 与符号两条产物证据见 `artifact-probe.log`

### 对话 #4 [2026-09-25]（第 1 棒：能力探针三轮）

- 问题: 上游用到 `/dev/net/tun`、`TUNSETIFF`、`chroot`/`setgid`/`setuid`、`poll`、
  `getaddrinfo`，构建主机上哪些能用？
- 操作: 写三份独立探针程序（`probe_caps{,2,3}.c`），每项在 `fork()` 子进程里跑；
  第 1 轮整进程被 SIGSYS(31) 打死 ⇒ 第 2 轮改逐项隔离；第 2 轮三处读数被自我否证
  （poll 夹具用了恒就绪 fd、`mknod` 打在只读 `/tmp`、`socket()` 成功后印了 errno 残值）
  ⇒ 第 3 轮全部重做，并补"必然不存在的设备名"作为**存在性对照**
- 结果: 读数汇总成本笔记的「能力矩阵」节；第 1/2 轮的原始日志与源码留在
  `~/tmp/uc2/z45-quicktun/` 作对照，不作结论用

### 对话 #5 [2026-09-25]（第 2 棒：取源合规与证据重跑）

- 问题: 提交态 `conandata.yml` 的 `url` 带 `gh-proxy.com` 镜像项（PF7 硬违规），
  且 `sha256` 字段的口径与注释描述可能不一致
- 操作: 读闸实装（`preflight.py:354-426`）确认镜像与 Debian 域两条硬规则 →
  删镜像只留官方原址；`curl` 实测该 URL（HTTP 200 / 22459 字节 / `sha256sum`）
  与 `sha256` 逐字对账 → 确认它是**归档自身哈希**、注释里的聚合哈希是另一件事，
  改写注释；同一闸函数对旧/新两版各跑一次取前后读数
- 结果: PF7 1 条 → 0 条；recipe revision 变更 ⇒ 按新 HEAD 重跑 conan-verify +
  finish，三条同判全绿（`finish3.log:86` + `.ci-result.json exit_code=0` +
  `reports/w3-local-ci.log:284 VERDICT: PASS`）；工作树里那两行镜像由框架回写产生，
  已按建 PR 前还原处理

### 对话 #6 [2026-09-25]（第 2 棒：B 判定与未覆盖面收口）

- 问题: 第 1 棒停在"dedup 近乎可判，但条件 2 容易被翻案"，没有交回结论
- 操作: 按 `经验文档/手册/03-路径B与C.md:80-89` 四条件，把 5 个面逐条做四范围查重
  （`tweetnacl`/`lsodium`/`链接期产物` 全库 0 命中；语义收窄 58 文件逐条扫面），
  层次差全部对齐到文件名+行号
- 结果: `B判定=create`（静默换后端一面），其余判 hit 并带行号引用；
  全过程落 `reports/knowledge-candidate-ledger.md`；TUN 一面顺带否证了
  既有条目"节点存在但被屏蔽"的推论，已按实测定口径

## 归档状态

- 归档状态: built（与 `manifest.yaml` 的 `status` 一致）

---

**编译结束**: 2026-09-25 19:17
**最终状态**: built
