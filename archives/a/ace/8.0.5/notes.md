# ace 8.0.5 适配笔记

## 编译环境
- 构建系统: makefile (ACE 传统 GNU Make + MPC/mwc.pl 生成 makefiles，无 configure)
- 编译日期: 2026-08-04
- 编译器: clang/clang++ 15.0.4 (aarch64-unknown-linux-ohos)
- 状态: built

## 编译步骤

ACE 8.0.5 新版源码结构为 `ACE/` + `TAO/` 分离，无 ACE_wrappers 目录，无 configure 脚本。
构建采用 ACE 传统 GNU Make 方式，需先用 MPC (mwc.pl) 生成 makefiles：

```bash
# 1. 下载 MPC（ACE 源码包不含 MPC 核心模块，需单独从 DOCGroup/MPC 获取）
#    ACE CI workflow 也独立 checkout MPC 到 workspace/MPC

# 2. 配置环境
export ACE_ROOT=/path/to/ACE
export MPC_ROOT=/path/to/MPC
# 3. 创建 ace/config.h（Conan build 内联生成；R8：无 __OHOS__ 条件编译）：
#    #include "ace/config-linux.h"
#    #undef ACE_HAS_UALARM / ACE_HAS_NETLINK / ACE_HAS_AIO_CALLS（若已定义）
#    #define ACE_LACKS_PTHREAD_CANCEL
# 4. 创建 include/makeinclude/platform_macros.GNU：
#    include platform_linux_clang.GNU
#    INSTALL_PREFIX + INSTALL_{BIN,LIB,INC,MAN} + 显式 INSBIN/INSLIB/INSINC/INSMAN
#    （GNU Make 4.4+：空 INSBIN 会变成 peer `/libACE.so.*` → make Error 2）
#    shared_libs / static_libs（E216，由 options.shared 写入）
# 5. 生成 makefiles
perl $ACE_ROOT/bin/mwc.pl -type gnuace ACE.mwc
# 6. 编译（E074/R9：必须 -j1；子库在子目录）
make -j1 ACE CC=... CXX=...
make -j1 -C Compression CC=... CXX=...
make -j1 -C ETCL CC=... CXX=...
make -j1 -C Monitor_Control CC=... CXX=...
# 7. 安装（各目录分别 make install）
make -j1 install ACE CC=... CXX=...
make -j1 -C Compression install CC=... CXX=...
make -j1 -C ETCL install CC=... CXX=...
make -j1 -C Monitor_Control install CC=... CXX=...
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | make 默认 CXX 指向 `/home/runner/work/ohos-make/...` 不存在路径 | 系统 make 内置 CXX 变量被 CI 环境硬编码 | make 命令行显式传 `CC=/data/service/hnp/bin/clang CXX=/data/service/hnp/bin/clang++` |
| 2 | `redefinition of 'sockaddr_storage'` | OHOS SDK 的 linux/socket.h 与 sys/socket.h 都定义 sockaddr_storage (E119) | config.h 中 `#undef ACE_HAS_NETLINK`，避免包含 linux/netlink.h |
| 3 | `::ualarm` 未声明 | OHOS musl 无 ualarm | config.h 中 `#undef ACE_HAS_UALARM` |
| 4 | `pthread_cancel`/`pthread_setcancelstate` 未声明 | OHOS 无 pthread cancel 支持 | config.h 中 `#define ACE_LACKS_PTHREAD_CANCEL` |
| 5 | `aio_read`/`aio_write`/`aio_suspend` 等未声明 | OHOS musl 无 POSIX AIO | config.h 中 `#undef ACE_HAS_AIO_CALLS` |
| 6 | `make install` 报 `MPC/prj_install.pl: inaccessible` | install 需要 MPC 目录 | 设 `MPC_ROOT=/path/to/MPC` 后重跑 install |
| 7 | 测试链接报 AIO Proactor 符号未定义 | config.h 更新后旧 .shobj/*.o 未重编，链接 libACE.so 含未定义符号 | 删除 Asynch_IO.o 等 AIO 相关 .o 强制重建 libACE.so |
| 8 | CI `make` Error 2；日志有 peer `/libACE.so.*` | GNU Make 4.4+ 多目标 install 规则中 `INSBIN` 为空 → 尝试写根路径 | platform_macros 显式设齐 `INSBIN/INSLIB/INSINC/INSMAN`；先编 ACE 再编依赖库 |
| 9 | CI #13168：`jobserver mkfifo: Operation not permitted` + `No rule to make target 'ACE_Monitor_Control'` | E074：HMDFS 禁 FIFO；Monitor_Control 等在 `ace/*/ ` 子目录，不在 `ace/` 顶层 makefile | `MAKEFLAGS=-j1` + 分目录 `make -j1`（对齐 afpfs-ng/argon2/R9） |

## 源码修改

- `ace/config.h`：由 Conan `build()` 内联生成 OHOS 适配宏（R8：无平台条件编译守卫；仅用于本配方 OHOS 构建）
- `include/makeinclude/platform_macros.GNU`：clang 平台 + INSTALL_PREFIX + E216 shared_libs/static_libs
- MPC 核心模块需单独下载（源码包不含），conan 配方双 source 固定 commit

## 依赖版本

- 产物为动态库（gnuace `shared_libs=1`）；E216 声明 `shared` 并写入 platform_macros，默认 `shared=True`；`shared=False` 在 validate 拒绝（对齐 bzip2 反向契约）
- MPC: DOCGroup/MPC 固定 commit `420e24790d349057e6463890ae993eb61eecc273`（源码包不含；勿用 floating `master`，保证 sha256 可复现）
- 无其他外部依赖

## 验证结果

```bash
# make check 等价：ACE 无 make check 目标，测试在 tests/ 目录
# 全量上游测试套件（run_test.lst 官方清单）共 276 项，OHOS 环境全部编译并逐一运行
# 2026-08-06 全量运行：217 PASS / 13 FAIL / 4 TIMEOUT / 37 SKIP / 5 NOBIN（可运行通过率 92.7%）
```

### 上游测试运行结果（OHOS 环境，2026-08-06 全量）

- 上游测试清单：`tests/run_test.lst` 共 276 项（官方 run_test.pl 执行清单；`tests/*.cpp` 源文件 293 个）
- 编译：`make -C ACE/tests all` 成功生成 283 个可执行测试，0 编译错误
- 逐项运行（每项 60s 超时）：**217 通过 / 13 失败 / 4 超时 / 37 平台跳过 / 5 未构建**
- 失败根因分类：
  - SIGSYS（rc=159，6 项）：Bug_3943/4055、Conn、Monotonic_* —— OHOS 内核未实现 syscall（clock_settime 等，E051 平台限制）
  - SIGSEGV（rc=139，3 项）：Bug_3911（mmap 共享内存）、OS_Test、Service_Config_Stream_Test —— 疑似平台差异，待排查
  - 断言失败（rc=1，4 项）：Bug_2610、FIFO（mkfifo 受限）、Sigset_Ops、TSS_Leak
  - 超时（4 项）：Bug_2772（上游注释已知易挂）、NonBlocking_Conn、Reactor_Fairness、Task_Wait —— 线程同步模型差异
- SKIP 37 项：按上游 run_test.lst 平台过滤声明跳过（MFC/Win32/VxWorks/LynxOS/PHARLAP 等）
- NOBIN 5 项：SSL 子模块（3）+ NDDS + Reference_Counted 参数变体（未编译）
- 完整逐项清单：`reports/full-test-results/results.txt`（复现脚本 `reports/run-ace-tests.sh`）

产物：libACE.so.8.0.5、libACE_Compression.so.8.0.5、libACE_RLECompression.so.8.0.5、
libACE_ETCL.so.8.0.5、libACE_ETCL_Parser.so.8.0.5、libACE_Monitor_Control.so.8.0.5（arm64 动态库）
---

**编译结束**: 2026-08-04 15:47
**最终状态**: built
