# libnfs 5.0.3 适配笔记

## 编译环境
- 构建系统: cmake（上游同时有 configure.ac，官方推荐 cmake）
- 编译日期: 2026-09-18
- 编译器: clang 15.0.4 / clang++（ohos-aarch64 profile）
- 平台: HarmonyOS PC (aarch64, OS=OHOS)
- 状态: built（conan-verify 全 PASS，本地 W3 通过）

## 上游信息
- 仓库: https://github.com/sahlberg/libnfs
- Tag: `libnfs-5.0.3`（commit `4379837`, 2024-02-10，old-API 分支最后一个版本）
- 源码 URL（官方，R39）:
  `https://github.com/sahlberg/libnfs/archive/refs/tags/libnfs-5.0.3.tar.gz`
- sha256: `d945cb4f4c8f82ee1f3640893a168810f794a28e1010bb007ec5add345e9df3e`
  （本机连续两次下载哈希一致，见 reports/）

## W0 依赖预检
- 上游 `configure.ac` / `cmake/ConfigureChecks.cmake` 实测**无外部库依赖**，
  仅探测 libc/pthread 头文件与函数；talloc/tevent、fuse、dispatch 均为可选
  （未命中即关闭）。
- 因此**没有需要 `conan download` 的 conan 依赖**（`build.dependencies: []`）。

## 编译步骤（探索阶段实跑）
```sh
# 官方 tarball 已预置到 $TMPDIR/builds（绕过 init_build 单 URL 的 SSL 容错缺陷）
python3 scripts/ohc-run.py init-build libnfs 5.0.3 --url=<官方 tar.gz>
cd $BUILD_SRC_DIR
cmake -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX -DCMAKE_BUILD_TYPE=Release \
      -DENABLE_UTILS=ON -DBUILD_SHARED_LIBS=OFF \
      -DCMAKE_POLICY_VERSION_MINIMUM=3.5 ..
make -j2
make install DESTDIR=$TEST_PREFIX
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 共享 libnfs.so 无 SONAME；CLI 的 DT_NEEDED 退化为相对路径 `../lib/libnfs.so`，安装后无法启动 | CMake 把 HarmonyOS 判为未知平台（"System is unknown to cmake: Platform/HarmonyOS"），不注入 `-Wl,-soname` | 按仓库惯例改**静态构建**（`BUILD_SHARED_LIBS=OFF`）；CLI 变自包含（NEEDED 仅 libc.so） |
| 2 | 上游用 `install(FILES ${CMAKE_CURRENT_BINARY_DIR}/${TARGET} ...)` 安装 CLI → 丢失可执行位，安装后 "Permission denied" | upstream CMake 安装规则错误 | patch 0003 改为 `install(TARGETS ${TARGET} RUNTIME DESTINATION ...)` |
| 3 | `writev` 隐式声明告警（int/ssize_t 截断隐患） | CMake 端缺少 `sys/uio.h` 探测（autotools 的 `AC_CHECK_HEADERS([sys/uio.h])` 有） | patch 0001/0002 在 `cmake/ConfigureChecks.cmake` + `config.h.cmake` 补 `HAVE_SYS_UIO_H` |
| 4 | 消费者直接 `#include <nfsc/libnfs.h>` 报 `struct timeval` incomplete type | 头文件在 `nfs_stat_64` 中内嵌 `struct timeval` 但不自行包含其定义头 | 文档 + test_package 中先 `#include <sys/time.h>`（上游既有约定，非缺陷） |
| 5 | `ctest` 50/50 FAILED | 上游每个用例都 `sudo exportfs` 启动内核 NFS 导出；设备无 `exportfs`、无 `/proc/fs/nfsd`，sudo 亦无法提权 | 平台限制，非库缺陷；见 R51 统计与 test_package/MANIFEST.yml |

## 源码修改（补丁，均由 `refresh-patch --auto` 生成）
- `0001-cmake-ConfigureChecks.cmake.patch` — 增加 `check_include_file("sys/uio.h" HAVE_SYS_UIO_H)`。
- `0002-cmake-config.h.cmake.patch` — 增加 `#cmakedefine HAVE_SYS_UIO_H`。
- `0003-utils-CMakeLists.txt.patch` — CLI 安装由 `install(FILES ...)` 改为 `install(TARGETS ... RUNTIME DESTINATION ...)`，修复可执行位/安装语义。

> 均为可移植性修复，**不含平台宏**（R8）。

## 依赖版本
- 无 conan 依赖；仅系统 libc / pthread。

## 验证结果

### conan-verify（G0-G4 + L2/L4/L5）
- 全部 PASS（见 `reports/`）。

### 鸿蒙真机断言（R34/R53）
1. 链接 `libnfs.a` 的 C 消费者程序，真机运行：
   ```
   PASS: nfs_init_context()
   PASS: nfs_parse_url_full() server=127.0.0.1 path=/export/dir file=/file.txt
   PASS: url fields validated
   PASS: nfs_destroy_url() + nfs_destroy_context()
   test libnfs 5.0.3: OK
   ```
2. CLI 产物（4 个，静态自包含）：
   ```
   nfs-ls  (no args) -> "Usage: nfs-ls ..."          rc=1
   nfs-cat (no args) -> "Usage: nfs-cat <file>"       rc=0
   nfs-cp  (no args) -> "Usage: nfs-cp <src> <dst>"   rc=0
   nfs-stat(no args) -> "Usage: nfs-stat <file>"      rc=0
   ```
3. 库导出符号：`nm libnfs.a | grep " T nfs_" | wc -l` = 155。

### 上游测试（R51 三步法）
- 清点：`tests/test_*.sh` 注册 **50** 个 CTest 用例（另 3 个 `.disabled`）。
- 实跑：`ENABLE_TESTS=ON` 构建成功，`ctest --timeout 15` → **50/50 FAILED**。
- 定性：全部为**平台限制**——用例统一经 `functions.sh:start_share()` 调
  `sudo exportfs`；设备无 `exportfs`、无 `/proc/fs/nfsd`，sudo 无 tty 无法提权
  （输出 `open /dev/tty for write failed`、`Failed to mount nfs share :
  nfs_service failed`）。非 libnfs 代码缺陷。
- 消费者侧替代断言（test_package）已覆盖 API 与 CLI 真机运行。

### 复现命令
```bash
# 消费者 API 测试
clang -O2 -o nfs_api_test nfs_api_test.c -I<prefix>/include -L<prefix>/lib -lnfs
./nfs_api_test   # 全 PASS
```

## 注意事项
1. **默认静态**：共享构建在 HarmonyOS 上会得到无 SONAME 的 .so（见问题 1），
   如需 `shared=True` 需另行处理 SONAME/RPATH。
2. `ENABLE_UTILS=ON` 是 CLI 产物的开关；`commands.json` 随软件声明（R38）。
3. 消费者包含头文件顺序：`<sys/time.h>` 必须在 `<nfsc/libnfs.h>` 之前。
4. 上游测试套件只对具备内核 NFS server（exportfs）的环境有意义。
---

**编译结束**: 2026-09-18 05:42
**最终状态**: built
