# webbench 1.5 适配笔记

## 软件简介
WebBench（Radim Kolar, 1997-2004）是简单的 **fork 型 HTTP/代理服务器压测工具**：
fork 出 N 个客户端进程，在 T 秒内持续请求目标 URL，最后报告 pages/min 与 bytes/sec。
它覆盖了 fork(2)、socket(2)/connect(2)、alarm(2)/sigaction(2)、pipe(2)、
fdopen(3)、gethostbyname(3) 等 POSIX 接口。许可证 GPL-2.0-or-later。

## 编译环境
- 构建系统: makefile（上游 GNU/BSD 兼容 Makefile）
- 目标平台: OpenHarmony OHOS / aarch64
- 编译器: clang（`aarch64-unknown-linux-ohos`）

## 编译步骤
```
make webbench CC=<OHOS clang> SHELL=<bash>
```
显式指定 `webbench` 目标——`all` 目标还会调用 `ctags`，对本适配无必要。

## 上游源码获取

**背景**：原始站点 `home.tiscali.cz` 已下线（HTTP 502）。webbench **从未进入任何
发行版的 distfile 池**——已实测 Debian pool（main/universe）、sources.debian.org API、
Gentoo distfiles、NetBSD pkgsrc、OpenBSD distfiles、MacPorts distfiles 全部 404。
上游无 GitHub release，也没有其他权威镜像。

**Internet Archive 快照（sha256 = 上游发布值）**：

| 核查项 | 结果 |
|--------|------|
| URL | `https://web.archive.org/web/20110727141838id_/http://home.tiscali.cz/~cz210552/distfiles/webbench-1.5.tar.gz` |
| sha256 | `285088dcd2c20a09f091af4156b4afac3fbc1c4281da1add51592c30d7d43066` |
| CDX 摘要 | 所有 200 状态的捕获（2011–2024）内容摘要一致（`DV6VAVPP7HOQ43QPCYGP4USAR4PUXTLP`） |
| gzip mtime | `Fri Jun 25 10:01:59 2004`，与 `debian/changelog` 的 1.5 发布日期（2004-06-25）吻合 |
| 目录结构 | 与上游自身 `make tar` 目标产物一致（上游自带 `debian/`） |

**但该 URL 无法被 conan 下载**：archive.org 以 `Content-Encoding: x-gzip` 配合
`Content-Length: 7675` 投递该文件，conan 的 source 下载器按 `Content-Encoding`
解压得到 30720 字节，随后与 Content-Length 不符而报错：

```
ConanConnectionError: Download failed, check server, possibly try again
Transfer interrupted before complete: 30720 < 7675
```

（curl 与 Python urllib 均能正常取到 7675 字节，问题仅存在于 conan 的下载器；
archive.org 的各种端点变体 `id_` / 非 `id_` / `http` / `%7E` / `Accept-Encoding: identity`
**均带该响应头**，无法规避。）

**最终采用的源**：同一上游发布的 GitHub 镜像，pin 到不可变 commit
`cnnewjohn/webbench@b7b358e3c895572d0cd1d24eec7df4b95d835864`：

```
https://github.com/cnnewjohn/webbench/archive/b7b358e3c895572d0cd1d24eec7df4b95d835864.tar.gz
sha256 92ed9f4ac06afcb9d89b5c947c30fe74139b15499cc4616ae3921df022b90438
```

**逐文件保真校验**（2026-09-24，对比 archive.org 的原始上游解包）：

| 文件 | 结果 |
|------|------|
| `Makefile` | **一致** |
| `socket.c` | **一致** |
| `webbench.1` | **一致** |
| `webbench.c` | **一致** |
| `debian/changelog` `debian/control` `debian/copyright` `debian/dirs` `debian/rules` | **全部一致** |
| `COPYRIGHT` `ChangeLog` | 上游为符号链接，git 按链接目标存储，故按构造即"不同"；其指向的文件（`debian/copyright`、`debian/changelog`）已一致 |

所有参与构建的文件与上游发布**逐字节一致**，**未修改任何源文件**。差异仅在 tar
容器：GitHub 以 commit 哈希作为根目录前缀，配方以 `strip_root=True` 去除。

## OHOS / 现代系统可移植性修改（在上游源码上做最小改写）

| # | 修改 | 原因 |
|---|------|------|
| 1 | `webbench.c`：删除 `#include <rpc/types.h>` | 见下方根因链一 |
| 2 | `webbench.c`：删除 `setvbuf(f,NULL,_IONBF,0);` | 见下方根因链二 |

### 关于修改 1 的完整根因链

**原始失败**（在三种环境下均复现）：

```
webbench.c:21:10: fatal error: rpc/types.h: No such file or directory
   21 | #include <rpc/types.h>
```

- WSL Ubuntu（glibc ≥ 2.26，未装 libtirpc-dev）：同样失败
- HarmonyOS OHOS（musl，clang 15.0.4）：同样失败

**根因**：`<rpc/types.h>` 是 Sun RPC 头文件。**glibc 2.26（2017）把 Sun RPC 从 libc
移出**，改由独立的 libtirpc 提供；该头文件只在装了 `libtirpc-dev` 时才存在。
musl（因而 OHOS）从来没有提供过它。上游 webbench 1.5 发布于 2004 年，当时
glibc 仍自带 Sun RPC。**这是现代系统回归，与 OHOS 无关**——在当代
Debian/Ubuntu 上编译上游原始 tarball 同样失败。

**该 include 是残留无用的**（已逐项实测）：

| 符号 | 实际来源 | OHOS 实测 |
|------|----------|-----------|
| `MAXHOSTNAMELEN` | `<sys/param.h>` | 存在，= 64 |
| `bzero` / `index` | `<strings.h>` | 可用 |
| `getopt_long` | `<getopt.h>` | 可用 |
| socket 接口 | `socket.c` | 可用 |

**修复**：删除该行，必要且充分——实测在删除后编译成功且压测正常运行。

### 根因链二：`setvbuf(_IONBF)` 使后续 `fscanf` 在 OHOS 上失效

**原始失败**（编译通过，但**运行结果全为 0**）：

```
$ webbench -c 2 -t 2 http://127.0.0.1:PORT/index.html
Some of our childrens died.
Speed=0 pages/min, 0 bytes/sec.
Requests: 0 susceed, 0 failed.
```

注意失败与成功**都为 0**——不是"少量失败"，而是**完全没有跑起来**。

**定位**：`webbench.c` 中父进程读取子进程结果的代码：

```c
f=fdopen(mypipe[0],"r");
if(f==NULL) { ... }
setvbuf(f,NULL,_IONBF,0);        /* <-- 384 行附近 */
speed=0; failed=0; bytes=0;
while(1) {
    pid=fscanf(f,"%d %d %d",&i,&j,&k);
    if(pid<2) { fprintf(stderr,"Some of our childrens died.\n"); break; }
```

**根因**：OHOS/musl 上，对**读流**调用 `setvbuf(stream, NULL, _IONBF, 0)` 之后，
该流上的 `fscanf` 返回 -1，且 `feof`/`ferror` 均为 0、`errno` 为 0——
即"无声失败"。父进程因此在 `pid<2` 分支退出，报告 "Some of our childrens died."
与 0 请求。

**在 OHOS 真机上的最小复现与排除**（同一份代码，仅切换读取方式）：

| 变体 | 结果 |
|------|------|
| `fscanf`（**带** `setvbuf(_IONBF)`） | **-1**（失败） |
| `fscanf`（**不带** `setvbuf`） | 3 ✓ |
| `fscanf`（父进程先关闭写端） | 3 ✓ |
| `fgets` + `sscanf` | ✓ |
| `fread` | ✓（读到 9 字节） |
| 裸 `read()` | ✓（读到 9 字节） |
| `fscanf` 读**普通文件** | 3 ✓ |
| `sscanf` 解析字符串 | 3 ✓ |

对照实验还证明：同一份源码在 **Linux x86-64/glibc** 上带该 `setvbuf` 也能正常压测
（实测 1590 请求全部成功）。因此这是 **OHOS/musl 的 stdio 行为差异**，
不是通用 bug；只有 `setvbuf(_IONBF)` + `fscanf` 这一组合会触发。

**修复**：删除该 `setvbuf` 调用。父进程的循环恰好执行 `clients` 次、
每次解析 3 个整数，**流的缓冲模式不可能改变解析结果**；管道 `read()` 在数据可用时
立即返回而不会等待填满缓冲区，因此读端采用默认（全缓冲）是安全的。
两个平台行为由此一致。

**修复后 OHOS 真机实测**（本地 127.0.0.1 HTTP 服务）：

| 并发 | 结果 |
|------|------|
| `-c 1 -t 3` | 30160 pages/min, 261386 B/s, **1508 susceed, 0 failed** |
| `-c 2 -t 3` | 37660 pages/min, 326386 B/s, **1883 susceed, 0 failed** |
| `-c 4 -t 3` | 39880 pages/min, 345861 B/s, **1994 susceed, 0 failed** |
| `-c 20 -t 3` | 40340 pages/min, 349613 B/s, **2017 susceed, 0 failed** |

不再出现 "Some of our childrens died."。

### 测试断言随之收紧

修复前 `test_package` 只断言 "0 failed"，而 OHOS 当时输出的是
`0 susceed, 0 failed`——**该断言会让"根本没跑起来"的结果通过**。
现已改为额外断言 **成功请求数严格大于 0**，并显式拒绝
"Some of our childrens died." 输出。断言数由 10 提升到 13。
这是本轮唯一一次**收紧**测试，不存在任何放松或减少。

## 上游测试
上游 **没有任何测试目标或测试目录**：

- `Makefile` 目标：`all`、`tags`、`install`、`webbench`、`webbench.o`、`clean`、`tar`
- `.PHONY: clean install all tar`
- 无 `test` / `check` 目标
- 解包后 9 个条目（含 `debian/`）中不存在 `tests/`、`test/`、`testing/`、`regression/`
- 仓库无 README / INSTALL / CONTRIBUTING，唯一文档是 `webbench.1` 与 `debian/`

如实记录：**upstream_total = 0**。功能验证放在 `test_package`（消费者视角）。

## 打包要点
- `bin/webbench`
- `share/man/man1/webbench.1`
- `share/doc/webbench/{COPYRIGHT,ChangeLog}`（上游以符号链接指向 `debian/`）
- `licenses/copyright`

## 已知上游行为（如实记录，未做规避）
`bench()` 以 `return i;` 结尾，而 `i` 是 `fscanf(f,"%d %d %d",&i,&j,&k)` 最后读入的值
（最后一个子进程的 pages 计数），**不是状态码**。因此压测成功时退出码是任意 0-255 值
（实测 223）。退出码仅在压测前的路径上有意义：`-V` → 0，无参数/`--help` → 2，
连接失败 → 1。测试据此断言 stdout 报告而非压测退出码。

## 功能验证设计
`test_package` 启动一个**仅绑定 127.0.0.1、随机端口**的本地 HTTP 服务
（`python3 -m http.server`，OHOS 实测 Python 3.12.8 可用），再对 `127.0.0.1` 执行
2 秒真实压测，并断言报告中失败请求数为 0。**不依赖任何公网站点**，结果不受外部
服务可用性影响。

## 验证结果
（等待 Harmony PC 真机 `conan create` 后填写）

<!-- notes-end -->
