# GlobalArrays (globalarrays) 5.9.2 — HarmonyOS PC 适配笔记

## 适配概况

- 上游：https://github.com/GlobalArrays/ga（PNNL），许可证 BSD-3-Clause，构建系统 Autotools。
- 设备端分支：`feat/globalarrays-5.9.2`（基于官方 upstream/main OID `951b76859a33b8e338351c70f716c572cd9872ca`）。
- 最终设备本地 CI：**PASS**（第 16 轮，通过率 6/6 断言，L0/L1/L4/L5 全过）。
- 模拟 Web Review：**PASS_WITH_WARNINGS**（无 High 级问题）。

## 关键决策：单进程 MPI 兼容层（降级适配）

globalarrays 是 PGAS（分区全局地址空间）分布式数组库，**所有消息层路径（MPI 与 TCGMSG-MPI）都硬依赖 MPI**：
- `GA_MSG_COMMS` m4 宏在 `with_mpi=yes` 与 `--with-mpi=no` 两个分支都强制 `ga_msg_comms=MPI`；
- `armci/src/collectives/message.c` 非 TCGMSG 分支无条件 `#include <mpi.h>`；
- `tcgmsg/tcgmsg-mpi/*.c`（6 个文件）同样 `#include <mpi.h>`（README 明言 TCGMSG-MPI 基于 MPI 实现）。

设备端与 conan 远程均无 MPI（`find /data/service/hnp -name mpi.h` 无结果；`conan list "mpi/*" -r ohpcd`、`openmpi/*`、`blas/*` 均 0 匹配）。经用户确认执行"选项 A"：

- 配方内置 `mpi_shim/mpi.h` + `mpi_shim.c`：**语义正确的单进程 MPI 子集**（size=1/rank=0），非空壳 stub——
  - `MPI_Comm_rank→0`、`MPI_Comm_size→1`；
  - `MPI_Barrier→空转`、`MPI_Allreduce/Allgather/Alltoall→本地 memmove`（单进程恒等语义）；
  - `MPI_Send/Recv→本地拷贝/空操作`、`MPI_Comm_c2f→comm 句柄`。
- **⚠️ 多进程 / PGAS 分布式能力 N/A（未运行）**：本适配以单进程模式构建并验证（GA_Initialize / NGA_Create / Put/Get 往返 / Inquire / 负向断言 6/6 PASS）。上游多进程测试集（global/testing 等依赖 MPI + mpiexec）未运行，PR 报告如实写 `N/A（未运行）`，不写 0/N。

## 补丁清单（5 个）

| 补丁 | 目的 |
|---|---|
| 0001-fix-autoconf-tmpdir-ohos.patch | 顶层 configure：autoconf 2.72 `umask 077 && mktemp -d "./confXXXXXX"` 在 HMDFS 上创建 `drwx--S---` setgid 目录不可写（Permission denied）→ 改 `${TMPDIR:-.}` + umask 022（dnsperf 同款先例） |
| 0002-fix-armci-configure-tmpdir-ohos.patch | armci/configure 同款 mktemp 坑 |
| 0003-fix-comex-configure-tmpdir-ohos.patch | comex/configure 同款 mktemp 坑 |
| 0004-guard-comex-mpi-tests-ohos.patch | comex 子 configure 的 `enable_mpi_tests` 缺 `with_mpi != xno` 守卫 → 无 MPI 时强制 MPI 链接测试失败；补丁参照 armci 已有守卫补齐 |
| 0005-spinlock-aarch64-ohos.patch | armci spinlock.h 无 aarch64 分支 → `SPINLOCK` 未定义 → locks.h `#error cannot run`；补丁添加 `__atomic_exchange_n`（LDXR/STXR）原子自旋锁分支 |

## 构建要点

- HMDFS 模式：mkdtemp 独立构建目录 + `/bin/sh` 脚本 + `CONFIG_SHELL=/bin/sh` + `TMPDIR=$HOME/tmp`（设备 /tmp 只读）。
- 显式 `--build/--host=aarch64-unknown-linux-ohos`（config.guess 无法识别 HarmonyOS）。
- `--with-mpi=no --with-sockets`（ARMCI TCP 网络）+ `--disable-shared --enable-static`（纯静态，规避 libtool relink 破坏 ELF 签名）+ `--disable-openmp`。
- CC/CXX 按 R33 从 conf `tools.build:compiler_executables` 解析（profile 注入），无则抛 ConanException。
- 产物 staging：libtool 归档在 `.libs/` 子目录需递归扫描；头文件含 `gaf2c/typesf2c.h`；`shutil.copy2` 字节级复制。
- package_info：`libs=["ga","armci","mpi"]`（libga.a 内含 ma/pario/tcgmsg/comex/cmx 对象）。

## 测试口径

- test_package（test_ga.c）6 个断言全部 PASS：GA_Nodeid、NGA_Create、Put/Get 往返、NGA_Inquire 维度 ×2、负向断言（ndim>MAXDIM → 返回 0）。
- 上游测试：N/A（未运行，依赖 MPI 多进程）。
- 未使用 assert()（-DNDEBUG 会移除）；C API 索引为 0-based（unit-tests 实证）；NGA_Put 的 ld 参数不能传 NULL（capi COPYC2F 解引用）。

## 遗留说明

- 单进程 MPI shim 为降级适配，多进程能力 N/A（未运行）；若后续引入 MPI 包可升级为全功能构建。
- conandata.yml 由 CI Mirror fallback 机制在跑批时改写（加 gh-proxy 前缀），交付前已恢复官方单 URL（R39）。
