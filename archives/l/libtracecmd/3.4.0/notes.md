# libtracecmd 3.4.0 适配笔记

## 上游与版本

- 官方仓库：`git://git.kernel.org/pub/scm/utils/trace-cmd/trace-cmd.git`
- 任务给出的版本 `3.4.0` = 上游 tag `trace-cmd-v3.4`（`Makefile` 里
  `TC_VERSION=3 TC_PATCHLEVEL=4 TC_EXTRAVERSION=0`）。但 CI worker 无法访问
  `git.kernel.org`，配方改用上游维护者 GitHub 镜像中同一 tag commit
  `3ce20923b3efa60d417da7acc8a327615fbd1419` 的归档：
  `https://github.com/rostedt/trace-cmd/archive/3ce20923b3efa60d417da7acc8a327615fbd1419.tar.gz`
  （sha256 `5e53c4fe…a3cb`）。未使用任何分支顶替版本。
- 交付的是该仓库里的 **库**（`lib/trace-cmd/` → `libtracecmd.so.1.5.5`，
  `LIBTRACECMD_VERSION = 1.5.5`），不是 `trace-cmd` 命令行程序。
- 许可：库是 LGPL-2.1（`COPYING.LIB`、`LICENSES/LGPL-2.1`）；`tracecmd/` 下的命令行
  程序是 GPL-2.0（`COPYING`），它只在构建目录里用来跑上游测试，不进包，所以包内
  没有 GPL 代码，`license` 写 `LGPL-2.1-only`。

## 依赖预检（R36 / R37）

- `GET /api/registry?keyword=libtrace` → `{"items":[],"total":0}`：制品仓里没有
  libtracecmd、也没有 **libtraceevent / libtracefs**。
- `git ls-tree -r --name-only origin/main -- archives | grep -iE 'libtracecmd|libtracefs|libtraceevent'`
  → 0 命中；main 里也没有同库同版本（R37 预检通过）。
- 但 libtracecmd 离不开这两个库：`include/trace-cmd/trace-cmd.h` 第 11-12 行就是
  `#include "event-parse.h"` / `#include "tracefs.h"`，`Makefile` 用 pkg-config 要求
  `libtraceevent >= 1.9`、`libtracefs >= 1.8`（`meson.build` 写 `>= 1.9.0 / >= 1.8.0`）。
  写进 `requires` 会直接撞 L0i/R36（依赖未发布）。
- 处置：把它们当**构建期输入**下载并整体静态链入（同 `archives/c/chezdav/3.0`、
  `archives/a/augustus-game/4.0.0` 等已合入并发布的先例）。版本取上游当前最新
  tag：libtraceevent `1.9.0`（tag commit `13701b5532e0`，sha256 `9ea83819…c61d5`）、
  libtracefs `1.8.3`（tag commit `6fad6a14ba0d`，sha256 `e8b81f96…d76c`），两者恰好
  满足 trace-cmd 3.4 自己的下限。二者同样使用上游维护者的 GitHub 镜像归档。
- 真正的 conan 依赖只有一个：`zlib/1.3.1.1`（制品仓 pull=1090，已发布）——用于
  `trace-compress-zlib.c` 的压缩段读写。`cunit/2.1-3`（制品仓 pull=56）以
  `test_requires` 提供，只给上游 CUnit 套件用，不进消费者依赖图。

## 打包形态（为什么 include/ 里会有别的库的头）

`--whole-archive` 把 libtraceevent.a + libtracefs.a 整体装进 `libtracecmd.so`，
真机实测该 `.so` 导出 587 个 `tep_* / tracefs_* / tracecmd_* / kbuffer_*` 符号，
`DT_NEEDED` 只有 `libc.so`（zlib 的归档也被吸收进去了）。因此：

- 消费者只 `-ltracecmd` 就能用，不会出现"libtracecmd 自己没引用到的 tep_* 符号缺失"。
- 静态形态同理：`package()` 把 `libtracecmd.a`、`libtraceevent.a`、`libtracefs.a`
  三者的目标文件并成一个 `libtracecmd.a`（46 个 .o），包里仍然只有一个库名。
- `trace-cmd.h` 里的 `#include "event-parse.h"` / `"tracefs.h"` 是硬要求，所以
  `include/` 交付 `trace-cmd/trace-cmd.h` + libtraceevent 的 4 个公共头 +
  libtracefs 的 `tracefs.h`。**只交付 conandata 里点名的 public headers**：
  libtracefs 的 `include/` 下还有个 `tracefs-local.h`，那是上游内部头，不进交付面。
- 随包附带 `lib/pkgconfig/libtracecmd.pc`，不写 `Requires: libtraceevent/…`——那两个
  `.pc` 在任何安装环境里都不存在。

## 构建要点（kbuild 风格 Makefile 的四个坑）

1. **`CFLAGS` 必须走环境变量而不是 make 命令行。** libtraceevent 是
   `CFLAGS := $(EXTRA_CFLAGS)`（第 128 行）会直接重置它，libtracefs 是
   `CFLAGS ?=`，而 trace-cmd 顶层 `override CFLAGS += $(INCLUDES)` 之后才 `descend`；
   make 命令行的同名变量经 MAKEFLAGS 覆盖到子 make，子 make 就把 `-I` 全丢了
   （实测 `tracefs-utils.c:20: fatal error: 'tracefs.h' file not found`）。所以
   `CC/AR/RANLIB/CFLAGS/LDFLAGS` 一律前缀成环境变量，`EXTRA_CFLAGS` 同时给一份；
   需要压过 `:=` 探测结果的（`TEST_LIBTRACEEVENT`、`LIBTRACEEVENT_LDLAGS`、
   `ZLIB_INSTALLED`、`NO_*`）才留在命令行。
2. **上游用 pkg-config 探测两个硬依赖。** 构建期输入不在系统搜索路径里，所以直接给
   判定与 flag（`TEST_LIBTRACEEVENT=y` + `LIBTRACEEVENT_CFLAGS/_LDLAGS`，libtracefs
   同理），不依赖 worker 上有没有 `.pc`。
3. **`nm` / `objcopy` 在 OHOS 工具链里只有 `llvm-*` 名字**，而 libtraceevent 的
   `scripts/utils.mk:redefine_local` 用 `nm` 生成 `--redefine-sym` 列表、
   `src/Makefile:23` 用 `objcopy` 落地静态库。不改上游 Makefile，在构建目录里放一层
   `tool-shims/` 转发脚本并前置到 `PATH`；worker 上有原生同名工具时不会被遮蔽。
4. **`bdir` 会被 descend 改写**（libtraceevent 的 `trace-utest` 落在 `utest/`，
   归档落在 `lib/`），配方用候选路径查找产物而不是猜目录。
5. **CI 镜像回退会把 `url` 从字符串改成列表。** CI 在 `conan create` 前会把 GitHub
   地址扩展成 `gh-proxy.com` 与原始地址两个候选，`conan_data["url"]` 因此可能是
   `list`。配方的 `_extract()` 同时接受字符串和列表，逐个调用 `get()`，失败时删除
   半包并继续下一个镜像；否则会报 `TypeError: expected str, bytes or PathLike object`。

## 补丁清单

| 补丁 | 目标树 | 原因 |
|---|---|---|
| `patches/0001-libtraceevent-btf-uapi-compat-and-qsort-r.patch` | bundled/libtraceevent 1.9.0 | OHOS SDK 的 `<linux/btf.h>` 早于 Linux 5.2：`BTF_KIND_MAX` 停在 `BTF_KIND_DATASEC`，`trace-btf.c` 用的 16..19 四个 kind 与 `struct btf_decl_tag`/`btf_enum64` 都没有，`NR_BTF_KINDS` 只有 16（用它索引 `btf_kind_str[]` 会越界）；另外 `qsort_r(3)` 是 GNU 扩展，OHOS libc 不提供（`llvm-nm` 查 sysroot 头里没有），clang 15 按隐式声明报错。全部 `#ifndef` 保护，新工具链仍用系统头。 |
| `patches/0002-trace-timesync-pin-threads-without-glibc-np-affinity.patch` | trace-cmd v3.4 | `lib/trace-cmd/trace-timesync.c` 调 `pthread_getaffinity_np()`/`pthread_setaffinity_np()`，OHOS `libc.so` 里只有 `sched_getaffinity`/`sched_setaffinity`（`llvm-nm -D` 实测），导致 `libtracecmd.so` 留下未定义符号、链接 `trace-cmd` 时 `ld.lld: error: undefined symbol: pthread_getaffinity_np`。沿用上游自己的 `test-build` 探测位（就在 `memfd_create` 旁边）加 `HAVE_PTHREAD_AFFINITY_NP`，把 5 个调用点收敛到两个 helper：有 `_np()` 时行为不变，没有时当前线程用 tid=0 的 `sched_*`，跨线程 pin（时钟同步工作线程）留给线程自身亲和性。 |

## 平台退化（都在配方里显式声明，不静默）

| 项 | 处置 | 依据 |
|---|---|---|
| zstd 压缩段 | `NO_LIBZSTD=1` | 真机上 `pkg-config libzstd` 命中的是 harmonybrew 的 `/opt/zstd`，既不是制品仓也不是系统库；链进去会让消费者依赖一个构建机路径。 |
| python 绑定 | `NO_PYTHON=1` | 设备与 worker 都没有 `swig`（`command -v swig` MISSING），上游本身也据此自动跳过。 |
| vsock 传输（`trace-cmd record -V`、guest 采集） | libtracefs 侧 `VSOCK_DEFINED=0`，trace-cmd 侧 `NO_VSOCK=1` | OHOS SDK 的 `<linux/vm_sockets.h>` 会带进旧版 `<linux/socket.h>`，与 `<sys/socket.h>` 的 `struct sockaddr_storage` 重定义（`tracefs-vsock.c` 同时包含两者）：`fatal error: redefinition of 'sockaddr_storage'`。 |
| KVM 时间同步、ptrace/audit 相关 | 由上游自己的探测处理 | `trace-timesync-kvm.o` 只在 `VSOCK_DEFINED=1` 时编；`libaudit` 不在环境里，上游探测会落 `NO_AUDIT=1`。 |
| udis86 反汇编 | 上游探测自动关闭 | 环境无 `udis86.h`。 |

## 真机验证（HarmonyOS PC / aarch64）

- 方式：OpenDesk 队列下发到 HarmonyOS PC（aarch64，clang 15），
  在设备私有目录执行 `conan create pkg -pr:b=<repo>/ci/conan/profiles/ohos-aarch64 -pr:h=<same> --build=missing`；
  作业 `20260928-235209-453f74-libtracecmd-old-repro`。
- 结果：`CREATE_EXIT:0`
- 上游 libtraceevent CUnit 套件（构建期输入，代码在本包内）：
  `tests 12 / ran 12 / passed 12 / failed 0`，`asserts 41/41`，
  `Elapsed time = 0.002 seconds`
- 上游 libtracecmd 套件：构建成功（`utest/trace-utest` 产出），执行按权限跳过，原因见
  `test_package/MANIFEST.yml`（tracefs 是 root:root 0755，构建用户无 CAP_SYS_ADMIN，
  无免密 sudo，8 项用例逐项要写 tracefs）
- 消费者测试 `test_package/test.c`：`checks 26, passed 26, failed 0`
- 产物：`lib/libtracecmd.so.1.5.5`(+`.so.1`/`.so` 符号链接)、`lib/libtracecmd.a`
  （46 个目标文件，含两个构建期输入）、`lib/pkgconfig/libtracecmd.pc`、
  `include/trace-cmd/trace-cmd.h` 与 5 个链入库的公共头、`licenses/COPYING.LIB`、
  `licenses/LICENSES/LGPL-2.1`；`.so` 的 `DT_NEEDED` 只有 `libc.so`，`RUNPATH` 为
  `$ORIGIN`。
