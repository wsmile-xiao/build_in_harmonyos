# libfabric 2.5.0 适配笔记

## 编译环境
- 构建系统: autotools (configure + make)
- 编译日期: 2026-05-27
- 编译器: clang/clang++ (OHOS cross-compile toolchain)
- 目标平台: aarch64-unknown-linux-ohos
- 状态: built

## 编译步骤

1. 下载源码 tarball: libfabric-2.5.0.tar.bz2
2. 解压并复制到 .work 目录 (init-build 已完成)
3. config.guess/config.sub 已由 init-build 预置 OHOS 适配补丁
4. 执行 configure: `./configure --prefix=/storage/Users/currentUser/usr/local --enable-monitor=no`
5. 执行 make -j1
6. 执行 make install DESTDIR=$TEST_PREFIX (staging 验证)

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | fstab.h not found (prov/hook/monitor) | OHOS 不提供 fstab.h 头文件 | 禁用 monitor provider: --enable-monitor=no |
| 2 | pthread_setaffinity_np undefined reference | OHOS (musl libc) 不提供此函数 | 在 osd.c 中添加 __OHOS__ 条件编译，与 __APPLE__ 同路径返回 -FI_ENOSYS |
| 3 | cpu_set_t 类型未定义 | musl libc 不提供 sched.h 中的 cpu_set_t | 在 osd.c typedef 条件中排除 __OHOS__ |
| 4 | ln hard link 失败 (HMDFS) | HMDFS 不支持硬链接 | libtool 自动回退到复制，非致命错误 |
| 5 | configure mktemp 无法创建相对路径临时目录 (HMDFS) | HMDFS 上 mktemp -d "./confXXXXXX" 失败 (相对路径) | 修改 configure mktemp 使用 ${TMPDIR} 绝对路径 |

## 源码修改

1. **config/config.guess**: OHOS 平台检测补丁 — 添加 __OHOS__ 和 HarmonyOS 检测，输出 aarch64-unknown-linux-ohos
2. **config/config.sub**: OHOS 目标支持补丁 — 添加 linux-ohos 和 ohos-linux 模式
3. **configure**: HMDFS 兼容补丁 — mktemp 使用 `${TMPDIR:-/storage/Users/currentUser/tmp}/confXXXXXX` 绝对路径替代 `./confXXXXXX`
4. **src/unix/osd.c**:
   - Line 62-65: `#elif defined __linux__ && !defined(__OHOS__)` 排除 OHOS 的 cpu_set_t typedef
   - Line 268: `#if !defined(__APPLE__) && !defined(__OHOS__)` 排除 OHOS 的 pthread_setaffinity_np 调用

## 依赖版本

- OHOS 工具链: clang-15 (aarch64-unknown-linux-ohos target)
- 无额外编译依赖

## 验证结果

```bash
# libfabric.so 是 ELF 64-bit LSB arm64 shared object
file libfabric.so.1.31.0
# ELF shared object, 64-bit LSB arm64, not stripped

# fi_info 是 ELF 64-bit LSB arm64 动态可执行文件
file fi_info
# ELF shared object, 64-bit LSB arm64, dynamic (/lib/ld-musl-aarch64.so.1), not stripped

# 无 RPATH
readelf -d libfabric.so.1.31.0 | grep -i rpath
# (无输出)

# .la 文件已删除 (R14)
# .pc 文件 prefix 正确，使用变量展开
```

## 交付物

| 文件 | 说明 |
|------|------|
| lib/libfabric.so.1.31.0 | 共享库 (主要交付物) |
| lib/libfabric.so / libfabric.so.1 | 符号链接 |
| lib/libfabric.a | 静态库 |
| lib/pkgconfig/libfabric.pc | pkg-config 文件 |
| bin/fi_info | 信息查询工具 |
| bin/fi_strerror | 错误码查询工具 |
| bin/fi_pingpong | 延迟测试工具 |
| include/rdma/*.h | 头文件 (fabric.h, fi_*.h) |
| include/rdma/providers/*.h | provider 头文件 |

## 注意事项

- monitor provider 被禁用（OHOS 无 fstab.h），不影响核心功能
- ofi_set_thread_affinity 在 OHOS 上返回 -FI_ENOSYS（线程亲和性不可用）
- HMDFS 上 /tmp 为只读文件系统，configure/config.status mktemp 必须使用 ${TMPDIR} 或用户目录绝对路径
- configure 补丁硬编码了 /storage/Users/currentUser/tmp 作为 TMPDIR 回退值（因 HMDFS /tmp 不可写）

## 上游测试用例执行结果（2026-08-28 实测）

### 上游测试结构

libfabric release tarball 中的上游测试只有一个：`make check` 运行 `util/fi_info` 二进制。
fabtests 是独立仓库（https://github.com/ofiwg/fabtests），不在 release tarball 中，不纳入本次测试。

### 执行结果

| 测试命令 | 结果 | 说明 |
|----------|------|------|
| `make check` | ✅ PASS (1/1) | make check 唯一测试项 util/fi_info 通过 |
| `./util/fi_info` | ✅ PASS | 正常输出 provider 列表（tcp/tcp;ofi_rxm 等），含 fabric/domain/version/type/protocol |
| `./util/fi_info -l` | ✅ PASS | 列出 16 个 provider：ofi_rxm, ofi_rxd, shm, udp, tcp, sockets, ofi_hook_perf/trace/debug/noop/hmem/dmabuf_peer_mem, off_coll, sm2, ofi_mrail, lnx |
| `./util/fi_info --version` | ✅ PASS | 输出 "libfabric: 2.5.0 / libfabric api: 2.5" |
| `./util/fi_info -e` | ✅ PASS | 正常输出全部 libfabric 环境变量说明 |

### 运行环境

- 交叉编译产物 `util/.libs/fi_info` 架构：ELF 64-bit LSB arm64, dynamic (/lib/ld-musl-aarch64.so.1)
- 本机为 aarch64 Linux（musl libc），可直接运行交叉编译产物
- fi_info 通过 libtool wrapper 脚本运行，自动设置 LD_LIBRARY_PATH 加载 .libs/libfabric.so

### 结论

上游 `make check` 全部通过（1/1 PASS），交叉编译产物在目标架构上运行正常，16 个 provider 全部可加载。
---

**编译结束**: 2026-08-28 14:02
**最终状态**: built
