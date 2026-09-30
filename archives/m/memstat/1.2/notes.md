# memstat 1.2 适配笔记

## 上游身份确认

`memstat` 这个名字在生态里有**两个**同名项目，选型时必须区分清楚：

| 项目 | 版本 | 判定 |
|------|------|------|
| `empiricalsoft/memstat`（Jeremy Maitin-Shepard，ncurses 内存可视化） | v1.x/v2.x | **仓库已 404 下线**，且其版本线没有 1.2 |
| `memstat`（Joshua M. Yelon / Michael Meskes，GPL-2.0，Debian main） | **1.2** | 本次适配对象 |

依据：GitHub API 对 `empiricalsoft/memstat` 的 repo / tags / releases 全部返回 404；
GitHub 全库搜索 `memstat` 无任何带 `v1.2` tag 的同名仓库。Debian 包 tracker
`memstat` 的 `testing` / `unstable` 版本为 **1.2**，与任务给定版本一致。

## 源码源选择（R39 / PF7）

上游 1.2 的原始 tarball 是 Debian pool 里的 `memstat_1.2.tar.xz`
（md5 `49bf5aa5f3006310e547a13b3275389a`，与 Ubuntu/Debian 公布校验和一致）。
但 **`deb.debian.org` 在本仓 PF7 源 URL 闸的硬黑名单内**
（`scripts/ohc/preflight.py:361 _PF7_DEBIAN_HOSTS`），写进 conandata.yml
会在建 PR 阶段被直接拦下。

替代方案选 **salsa.debian.org（Debian 官方 Git 托管）**：

- `memstat` 是 Debian **native 包**（版本 1.2 不带 debian revision），
  因此 salsa 仓库里的源码树就是**未经改动的上游 1.2 原件**。已逐文件核对
  md5：`memstat.c` / `Makefile` / `memstat.conf` / `memstat.1` /
  `memstat-tutorial.txt` 与 `memstat_1.2.tar.xz` **全部一致**。
- URL 固定到不可变 tag `debian/1.2`（commit `00187c85f6`）而非分支头，
  连续两次拉取 sha256 相同（`e4811be9...`），杜绝内容漂移。
- salsa.debian.org 不在 PF7 黑名单（黑名单只含 gh-proxy 类镜像、
  Debian pool、gitcode/gitee 搬运源等），且属官方托管而非第三方镜像。

salsa archive 会多带一个 `debian/` 目录（打包脚本，不参与编译，无影响）。

## 依赖（W0）

`conan download "<pkg>/<ver>" -r=ohpcd --only-recipe`：**无需检查——本包零三方依赖**。
`memstat.c` 只 include 标准 POSIX 头（stdlib/string/sys-*/dirent/stdio/unistd/getopt/errno），
`debian/control` 的 Build-Depends 除 debhelper 外为空，Makefile 无任何外部库。
因此配方 `requires` 为空，不存在 R36 依赖未发布风险。

## CI 能力矩阵（W0b）

构建只需 make + C 编译器（全在 CI 能力矩阵 ✅ 档），无 autotools / cmake / perl /
python 依赖，因此不需要任何 `tool_requires`。本仓 `archives/m/memstat/` 下
**无历史归档**（`git grep -l memstat origin/main -- archives` 只命中同名前缀的
`smemstat` 与无关的 `libmemcached` 补丁），故无历史 notes 可比对，也无
"设备原生成功不可迁移"的风险面。

## OHOS 适配要点

编译层面唯一的问题是 libc 差异——OHOS 用 musl 系 libc，上游代码是照 glibc 写的。
**只改了一处源码、一个补丁文件**，三处修改全部是无平台宏的纯 C 改动
（R8：未引入 `__OHOS__` 等任何平台宏），且在 glibc 下同样编译通过、行为不变。

### 1. `PATH_MAX` 未声明 → `#include <limits.h>`

`read_proc()` 用 `PATH_MAX` 给 maps 行缓冲区定长，但源码没 include `<limits.h>`。
glibc 下由其它头文件**传递引入**，所以上游一直能编；OHOS libc 不传递引入，
第一行声明就 `use of undeclared identifier 'PATH_MAX'`，随后 `buff`/`path`/`perm`
的每一处使用全部级联报错。

### 2. `perm[4]` 越界写 → 改成 `perm[5]`

```c
sscanf(buff, "%lx %lx %4s %lx %s %s %lu %ms", ..., perm, ...);
```

`%4s` 最多写 4 个字符**加结尾 NUL = 5 字节**，而 `perm` 只有 4 字节 →
每次解析 maps 行都越界写 1 字节。OHOS 工具链直接报
`-Wfortify-source: destination buffer in argument 5 has size 4, but the
corresponding specifier may require size 5`。按字段宽度补足为 `perm[5]`。

### 3. musl `strtol` 对非数字串置 EINVAL → 用 endptr 判别（**关键修复**）

```c
errno = 0;
pid = strtol(ent->d_name, NULL, 10);
if (errno != 0) { perror("strtol"); exit(1); }
```

`readdir("/proc")` 的第一个条目是 `"."`。`strtol(".", NULL, 10)`：

- **glibc**：无转换发生，**errno 保持不变** → 上游判断恒不触发，一切正常；
- **musl（OHOS）**：无数字时**显式 `errno = EINVAL`** → 上游把"非数字目录名"
  当成解析失败，直接 `strtol: Invalid argument` + `exit(1)`。

后果是 memstat 在 OHOS 上**完全不可用**：任何一次扫描都在第一个目录项就退出，
连一行报告都打印不出来。这正是"glibc 上看不见、OHOS 上必炸"的典型 musl 差异。

修法是区分"根本没发生转换"（endptr 仍指开头，即 `.`/`..`/`self`/`sys` 这类
非数字 /proc 条目，直接 `continue` 跳过）与"真的溢出"（`errno != 0` 才报错）。
原来的溢出检测语义完整保留。

**该缺陷是本次适配唯一的实质性平台修复**，test_package 的用例 3/4/5
（`-p <self>` 扫描、独占过滤、不存在 pid）都是它的回归测试：
打补丁前这三条在 OHOS 上全部失败（`strtol: Invalid argument` + exit 1），
打补丁后通过。

## 构建配方决策

- 构建系统：手写 Makefile（3 个 target，无 configure），`build()` 直接
  `make CC=<conf> CFLAGS='-O2 -Wall' -j1`。
- R33：编译器取自 `self.conf.get("tools.build:compiler_executables:c")`，
  **不使用** `${CC}` / `${CFLAGS}` shell 变量（release worker 上为空会静默失败）。
- 命令行传 `CFLAGS` 是刻意的：Makefile 里写的是 `CFLAGS += -g -Wall -O2`，
  而命令行变量优先级高于 Makefile 内的 `+=`（否则 `+=` 会被忽略），
  这样才能真正控制编译选项，并去掉 Release 包不需要的 `-g`。
- R9：`-j1`，不用 `-j$(nproc)`。
- R32：`validate()` 用 `not in ("Linux", "OHOS")` 判断，未使用 `== "Linux"`。
- R26：适用性已核——本包不产出库文件，无系统同名库，不涉及静态/动态取舍。
- R49：无三方依赖，不需要注入任何 prefix，故未触碰 `SYS_PREFIX`/`/usr/local`。
- R38：产物是可执行文件 → 已建软件级 `archives/m/memstat/commands.json`
  （`name`/`type=tool`/`versions.ref` 与版本对齐），`package_type="application"`。

## 产物布局

| 路径 | 内容 |
|------|------|
| `bin/memstat` | 可执行文件（`package_type=application`） |
| `etc/memstat.conf` | inode→路径解析的扫描目录清单，同上游 `$(DESTDIR)/etc` 布局 |
| `share/man/man1/memstat.1` | man page |

## 已知限制

- memstat 硬编码读取 `/etc/memstat.conf`。仅当某个映射没有路径、需要靠 inode
  反查文件时才需要该文件；缺文件时 `scan_fpath()` 会 `exit(1)`。因此运行
  `-n`（numeric，跳过 inode 反查）不需要该文件，CI 与 test_package 全部用 `-n`。
  配方已把 `memstat.conf` 打进包的 `etc/`，但 conan 包的 `etc/` 不在运行时
  `/etc` 路径上——这是打包惯例的固有限制，不影响 `-n` 用法。
- `usage()` 里硬编码打印版本号 `"1.0"`（上游自 1998 年起未更新），
  本次**未改动**：它不影响任何功能，test_package 也不依赖该字符串，
  保持补丁最小化。已在此记录以免后续误判为适配缺陷。
- memstat 需要访问 `/proc`。作为诊断工具在受限环境（非 root、部分 PID 的
  maps 不可读）下会看到不完整的报告，这是设计使然，不是适配问题。
