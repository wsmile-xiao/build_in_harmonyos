# rdma-core 61.0 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-16
- 编译器: clang/clang++ (LLVM 15.0.4, OHOS SDK 26.0.0.18)
- 状态: built

## 编译步骤

```bash
# 源码: 官方 GitHub release v61.0
#   https://github.com/linux-rdma/rdma-core/releases/download/v61.0/rdma-core-61.0.tar.gz
#   SHA-256: 340be509137103677ea30798d6ffe64a991148dae333b79a5bc0744e219fde2f
mkdir build && cd build
cmake .. \
    -DCMAKE_BUILD_TYPE=Release \
    -DENABLE_RESOLVE_NEIGH=0 \
    -DNO_PYVERBS=1 \
    -DNO_MAN_PAGES=1 \
    -DENABLE_STATIC=1 \
    -DNO_COMPAT_SYMS=1 \
    -DENABLE_VALGRIND=0 \
    -DENABLE_WERROR=OFF \
    -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX \
    -DCMAKE_C_FLAGS="-D__MUSL__=1" \
    -DCMAKE_CXX_FLAGS="-D__MUSL__=1"
make -j2
make install DESTDIR=$TEST_PREFIX
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | sockaddr_storage redefinition (E119) | OHOS 同时包含 linux/socket.h 与 sys/socket.h 时重定义 | netlink-attr.h 移除 netdb.h 改前置声明 + 配方注入 __MUSL__=1（patch 0001） |
| 2 | undefined symbol: rindex | OHOS musl 不导出 BSD 废弃函数 rindex | srp_daemon.c 改为 strrchr()（patch 0006） |
| 3 | program_invocation_short_name undeclared | OHOS musl 无 glibc 扩展符号 | preload.c 改用 __progname（patch 0005） |
| 4 | getpass implicit declaration | OHOS musl 无 getpass GNU 扩展 | ibdiag_common 弱声明 + 弱符号实现（patch 0002/0003） |
| 5 | undefined symbol: pthread_cancel | OHOS musl 无 POSIX 线程取消 API | rping 改 SIGUSR1 处理函数 + pthread_kill + join（patch 0004, E513） |
| 6 | cmake_install "bin/srp_daemon is not a directory" | conan 工具链 CMAKE_INSTALL_LIBEXECDIR 默认=bin | 配方 generate() 覆盖 CMAKE_INSTALL_LIBEXECDIR=libexec |
| 7 | test_package 运行期 dlopen 包内共享库受限 | OHOS 运行期加载器对部分包内 .so 报 EACCES | test_package 静态链接包内 .a，消除运行期加载依赖 |

## 源码修改

patches/ 共 6 个补丁（详见 conandata.yml 与 patch_classification）：
- 0001 buildlib/fixup-include/netlink-attr.h —— E119 sockaddr_storage 前置声明
- 0002/0003 infiniband-diags/ibdiag_common.{c,h} —— getpass 弱符号实现
- 0004 librdmacm/examples/rping.c —— pthread_cancel → 信号式线程退出（E513）
- 0005 librdmacm/preload.c —— program_invocation_short_name → __progname
- 0006 srp_daemon/srp_daemon.c —— rindex → strrchr

## 依赖版本

- 无外部 conan 依赖（libnl/pyverbs/man 页/valgrind 全部禁用）
- 系统依赖: pthread, rt, dl

## 验证结果

- 手动 cmake 构建 100% 通过（60 个 bin 工具 + libibverbs/librdmacm/libibumad/libibmad/libibnetdisc 及 provider 库）
- 上游测试: 8 个 C 测试二进制全部构建运行；bitmap_test/umad_compile_test/umad_reg2/umad_register2/ibsendtrap PASS；
  umad_sa_mcm_rereg_test/testleaks/mcm_rereg_test 依赖真实 RDMA 硬件，OHOS 无设备（退出码 255/1/139 记录在案）
- Python 测试: 50 个 pyverbs 测试模块因 NO_PYVERBS=1 + 无 RDMA 硬件未实例化（已计入台账）
- test_package: conan-verify G0-G4 + L2/L4/L5 全 PASS；test_rdma-core / test_ohos_specific / test_consumer 实跑 PASS
- 双口径: 8/8 C 测试声明并实例化，5 通过、3 硬件阻塞（5/8=62.5% 全量通过率；5/5 可执行集合 100%）

## 知识沉淀

- 知识候选台账: reports/knowledge-candidate-ledger.md（6 项候选，七轴查重）
- 新增草稿: knowledge/drafts/DRAFT-rdma-core-61.0-rindex-strrchr.{kv,md}、
  knowledge/drafts/DRAFT-rdma-core-61.0-conan-libexecdir-bin-collision.{kv,md}
- 复用既有: E091/E119（sockaddr_storage）、E093（getpass）、E493/E203（__progname）、E513（pthread_cancel）

## 注意事项

- OHOS 无 RDMA 硬件，ibv_get_device_list 返回 0 设备属正常（56.1 笔记同口径）
- W3 基线隔离复验: archives/c/cloog/0.21.1/.build-closed 与 .staging-verified 为
  提交前已存在的其他库基线空文件，隔离复跑 W3 后已原样恢复（SHA-256 e3b0c442… 一致）
---

**编译结束**: 2026-09-16 17:28
**最终状态**: built
