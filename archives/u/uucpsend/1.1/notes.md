# uucpsend 1.1 — 适配笔记

## 1. 这是什么

`uucpsend` 是 Martin Schulze 写的 INN 新闻批处理前端，用来替代 INN 自带的
`send-uucp` 脚本。它本身**不做**批处理，而是按站点控制文件驱动一堆既有工具：

```
读 uucpsend.ctl
  └─ 每站点：
       makelock()                     在 /var/run/innd/LOCK.<site> 上锁
       df -P /var/spool/uucp          检查 spool 剩余空间
       ctlinnd -s -t30 flush <site>   让 INN 把待发文章刷进 <site>.uucp
       cat/mv/rm/sort                 与上一轮残留的 <site>.work 合并去重
       du -s /var/spool/uucp/<site>   检查站点队列上限
       batcher -B.. -b.. -p "<uuxcmd>" <site> <site>.uucp
         └─ uuxcmd = ( echo "#! <header>" ; <compressor> ) \
                     | uux - -gd <uuxargs> <site>!rnews
```

代码量很小：`uucpsend.c` 620 行 + `log.c` 75 行，K&R 风格 C。

## 2. 构建系统

上游只有一份手写 POSIX Makefile，没有 configure / CMake / meson，
**也没有任何测试**——Makefile 里只有 `uucpsend`、`clean`、`install` 三个目标，
连 `all` 都没有（`make` 裸调会直接报 "No rule to make target 'all'"）。

```
uucpsend-1.1/
  Makefile        uucpsend.c  log.c  log.h  paths.h
  uucpsend.ctl    uucpsend.8  uucpsend.ctl.5  readme  ChangeLog  COPYING
```

## 3. 上游源码的三处问题

### 3.1 Makefile 把工具链和安装布局写死

```make
CC = gcc
CFLAGS = -O3 -Wall
STRIP=-s
DEST=
```

- `CC = gcc` 是 make 普通赋值，**会覆盖环境变量**。Conan 通过 `conanbuild`
  环境脚本导出的 `CC` 会被它盖掉，只有命令行 `make CC=...` 才生效。
- `STRIP=-s` 无条件 strip，debug / relwithdebinfo 构建拿不到符号。
- `install` 规则无 DESTDIR，且无条件传 `-o root -g root`：
  非 root 构建用户必然 EPERM；而想用 `OWNER=` 清空的常规做法在这里无效，
  因为该规则没有把 owner 参数变量化，`install -o -g ...` 会把下一个参数
  当成 owner 名吞掉。
- `SHELL = /bin/bash` 不是每个 POSIX 目标都有（OHOS 只有 `/bin/sh`）。

补丁 `0001` 的处理：`all:` 默认目标；`CC/CFLAGS/CPPFLAGS/LDFLAGS` 改 `?=`；
`STRIP=$(if $(DEBUG),,-s)`；`DESTDIR` + 可覆盖的 `BINDIR/CONFDIR/MANDIR`
（保持上游默认位置 `/usr/lib/news/bin`、`/etc/news`、`/usr/man`）；install
规则改为 `mkdir -p` + `install -m`，不再尝试改 ownership；`SHELL=/bin/sh`。

> 注意 `uucpsend: $(OBJS)` 是**无命令行的规则**，它本身不产生链接步骤——
> 真正把 `uucpsend.o` + `log.o` 链成 `uucpsend` 的是 make 内建的 `%: %.o`
> 规则。所以上游 `make uucpsend` 一直是能工作的，补丁把这条规则换成
> `all: uucpsend` 不会改变行为。

### 3.2 `<malloc.h>` / `index()`

- `#include <malloc.h>`：glibc/BSD 扩展头，musl（OHOS libc）**不提供**。
  `malloc()/free()` 本来就由已在文件里 include 的 `<stdlib.h>` 声明。
- `index(cp, DELIMITER)` 5 处：BSD/旧 POSIX 的 `strchr()` 别名，
  POSIX.1-2008 已撤销。musl 只在 `_BSD_SOURCE` 下声明它。

补丁 `0002` 删除 `<malloc.h>`、`index()` → `strchr()`（行为完全一致）。

### 3.3 `free_sites()` 在 clang 下是硬错误（真机首轮构建实测发现）

```c
void
free_sites(root)
struct s_sites *root;              /* <-- 这个 tag 在程序里根本不存在 */
{
  struct s_site *act;
  (struct s_sites *)act = (struct s_sites *)root;   /* <-- 对 cast 赋值 */
```

`struct s_sites` 全程序未声明（只有 `struct s_site`），该形参因此得到一个
仅在本函数内可见的不完整类型。于是：

```
uucpsend.c:288:3: error: assignment to cast is illegal,
                  lvalue casts are not supported
```

GCC 历来只给警告，clang 15 直接报**硬错误**——即未打补丁的上游源码在
OHOS 工具链下**完全无法编译**。同时 3 处调用点传的都是 `struct s_site *`，
触发 `-Wincompatible-pointer-types`。

补丁 `0003` 把形参改为 `struct s_site *` 并直接赋值，既消除编译错误也消除
那 3 条指针类型警告，行为不变（函数只经 `->next` 遍历并释放
`name`/`header`/`compressor`/`uuxargs`，这些成员都声明在 `struct s_site` 上）。

> Debian 以 `0002-uucpsend.c-Don-t-cast-lvalue-in-assignment.patch`
> （Andreas Jochens，Debian bug #297738）携带同一处修正；本补丁是依据
> 编译器诊断独立得到，结论一致。

### 3.4 `paths.h` 编译期硬编码绝对路径（未改，属设计而非缺陷）

```c
#define _PATH_LOCKS    "/var/run/innd"
#define _PATH_BATCHDIR "/var/spool/news/out.going"
#define _PATH_NEWSBIN  "/usr/lib/news/bin"
#define _PATH_MOST_LOGS "/var/log/news"
#define PATH_UUX       "/usr/bin/uux"
...
```

这些正是 INN + Taylor UUCP 的标准安装位置，改成可配置属于功能变更，
超出「让它在 OHOS 上编译并打包」的范围，因此**保持原样**。
后果需要如实记录（见第 5 节）。

## 4. 依赖结论

### 4.1 链接期：零依赖

程序只用 libc（`stdio/stdlib/unistd/string/sys/stat`），没有任何第三方
链接符号。INN 与 UUCP 的耦合**全部通过 `system(3)`/`popen(3)` 子进程**发生，
所以配方 `requirements()` 为空，`uucpsend` 可以独立编译、独立打包。

### 4.2 运行期：需要 INN 与 Taylor UUCP（不建模为 Conan 依赖）

| 外部程序 | 上游路径 | 提供者 | 制品仓状态 |
|---|---|---|---|
| `ctlinnd` | `/usr/lib/news/bin/ctlinnd` | `inn2/2.7.4` | **已发布** |
| `batcher` | `/usr/lib/news/bin/batcher` | `inn2/2.7.4` | **已发布** |
| `uux` | `/usr/bin/uux` | `uucp/1.07` | **缺失** |
| `df`/`du`/`sort`/`mv`/`cat`/`rm` | 系统路径 | 系统工具 | 取决于部署 |

W0 实测证据（2026-10-02，本机 conan 2.29.1）：

```
$ conan list "inn2/2.7.4:*" -r=ohpcd
  ... 21b17f8b2bc0e9511e276e3d57a23893067cefe5  os=OHOS 6.0 arch=armv8 Release
$ conan download inn2/2.7.4 -r=ohpcd --only-recipe
  Download completed in 0s

$ conan list "uucp/*" -r=ohpcd
  WARN: There are no matching recipe references
$ conan list "uucp/1.07:*" -r=ohpcd
  ERROR: error:system acceleration policy not enabled. [Remote: ohpcd]
$ conan download uucp/1.07 -r=ohpcd --only-recipe
  ERROR: error:system acceleration policy not enabled. [Remote: ohpcd]
```

`uucp/1.07` 的配方本体**已经在 main 里**（commit `5b8165f5ad`，
`archives/u/uucp/1.07/`，含 13 个 bin 产物与 `commands.json`），但其
`manifest.yaml` 仍是 `status: built`，且制品仓查询/下载均失败——**尚未发布**。

**处置决定**：不把 `uucp`/`inn2` 写进 `requires()`。理由是它们不是链接期
依赖，写进去只会让 `uucpsend` 的包图被一个未发布的包卡住，而不会让任何
功能变得可用（真正的可用性取决于部署机上的 INN spool 与 UUCP 传输）。
依赖缺口作为运行期前置条件记录在 `manifest.yaml` 的
`runtime_prerequisites` 与本节，不混入本 PR。

## 5. 本包能做什么 / 不能做什么

**已具备**：编译出 `bin/uucpsend`；正确解析控制文件；正确处理
`-c` / `-f` / 站点名参数；日志在 `/var/log/news` 缺失时回退到 stderr。

**不具备（环境归因，非配方缺陷）**：在没有任何 INN/UUCP 部署的机器上，
`loopthrough()` 会在 `makelock()`（`/var/run/innd` 不存在）或
`ctlinnd flush`（二进制不存在）处停下，因此**不会真正投递新闻批**。
这是上游设计使然——它本来就是一个驱动外部工具的胶水程序。

## 6. 测试口径

上游零测试资产，`make check` 不存在，配方不虚构通过率。
`test_package/test_uucpsend.sh` 的 15 条断言覆盖可在独立包上观测的行为：

1. 合法控制文件被接受、解析出的站点被驱动（exit 0，`start alpha`，并到达
   两种确定终态之一：完整周期 `end alpha`，或无 INN 部署时
   `Can't open lock file` 后跳过）
2. 畸形行报 `invalid line` 且带文件名与行号，且不中断整轮运行
3. `-f <appendix>` 追加控制文件路径生效
4. 显式站点名选择生效
5. 控制文件缺失时报 `Can't open file` 且非零退出（实测 exit 255）
6. 日志目录缺失时回退到 stderr

期望输出经 `parse_ctlfile()` / `extract_site()` / `trimm_sites()` 的逐行转写
核对（`reports/local-verification.md` 第 4 节）。

**真机实跑 15/15 通过**（`reports/device-build.md`）。断言数由 17 调整为 15：
首轮失败的一条是我的断言写错——`makelock()` 写 `/var/run/innd/LOCK.<site>`
（`paths.h` 硬编码），无 INN 部署时该目录不存在，程序报 "Can't open lock file"
后 `continue`，在 `end <site>` 之前就跳出。这是无 INN 主机上的正确行为，
已改为接受两种确定终态之一；被检查的实质行为一条未减。

## 7. 下一步

见 `reports/next-steps.md`。
