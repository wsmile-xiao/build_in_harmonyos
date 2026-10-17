# mergerfs 2.40.2 适配笔记

## 编译环境
- 构建系统: 纯 Makefile（上游 `make`，无 configure/CMake）
- 目标: OHOS aarch64（Conan `os=OHOS, arch=armv8`）
- 编译器: clang / clang++（OHOS SDK），归档 llvm-ar

## 上游形态

mergerfs 是一个基于 FUSE 的联合文件系统。2.40.2 的官方源码包是**自包含**的：
它自带（vendored）一个 libfuse 2.x 的改造分支，以及 wyhash、ghc::filesystem、
fmt、optional-lite、concurrentqueue、scope_guard。因此**没有任何外部依赖**，
`libfuse/`、`src/*.cpp` 全部随包编译进 `build/mergerfs` 一个二进制。

构建目标：

| 目标 | 产物 |
|------|------|
| `make` / `make tests` | `build/mergerfs`（主程序） |
| `make tests` | `build/tests`（acutest 单元套件） |
| `make preload` | `build/preload.so`（LD_PRELOAD 辅助库） |
| `make -C libfuse` 的 `all` | `build/libfuse.a`，以及（当 `uname -s == Linux` 时）`mergerfs-fusermount`、`mount.mergerfs` |

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 链接期 `undefined symbol: pthread_cancel` / `pthread_setcancelstate` | OHOS bionic 未实现 POSIX 线程取消；vendored libfuse 的 `lib/fuse.c`、`lib/fuse_loop.cpp` 引用了这两个符号 | 补丁 `0001-libfuse-guard-pthread-cancellation.patch`：两处调用用 `HAVE_PTHREAD_CANCEL` 特性宏守卫（未定义 = 0 → OHOS 省略），`fuse_stop_maintenance_thread` 在无取消能力时改为 `pthread_detach`。与制品仓 libfuse/3.18.2 配方的 `HAVE_PTHREAD_CANCEL` 处理口径一致 |
| 2 | 链接期 `cannot find -lrt` | OHOS 把 librt 并入 libc，没有独立 librt；上游两个 Makefile 都固定追加 `-lrt` | 在 `conanfile.py` 以**命令行** `LDFLAGS="-pthread"` 覆盖：GNU make 中命令行变量会整体覆盖 Makefile 里对同名变量的 `:=` 赋值（含追加），因此 `-lrt` 不再出现。不改上游 Makefile |
| 3 | `tests/TEST_*` 集成脚本无法运行 | 这 5 个脚本通过 `tests/run-tests <挂载点>` 验证**已挂载**的 mergerfs 语义，需要真实挂载，即需要可访问的 `/dev/fuse` | OHOS 沙箱对 `/dev/fuse` 拒绝访问（`Permission denied`，与 afuse/ext2fuse 一致）→ 集成脚本如实记为阻塞，不伪造；单元套件（不依赖 FUSE）在 `build()` 内实跑 |
| 4 | `make tests` 本身无法编译（`tests/tests.cpp`：`FUSE::ReadDir` 报错） | 上游 2.40.2 tarball 的 `tests/tests.cpp` 已过期：`test_config_readdir` 仍用旧的全局 `ReadDir` 枚举 API；源码已改为 `FUSE::ReadDir` 字符串构造。上游 CI（`.cirrus.yml`）只跑 `make`/`make deb`/`gmake`，从不构建 `tests`，所以发布包里该文件是坏的 | 补丁 `0003` 只把这一个用例改到当前 API，其余不动、用例数仍 15 |
| 5 | `make preload` 报 `redefinition of 'openat'/'fopen'/'creat'` | `_FILE_OFFSET_BITS=64` 下 OHOS 的 fcntl.h/stdio.h 把 `open64/openat64/fopen64/creat64` 定义为指向非 64 位函数的宏，而 `tools/preload.c` 两套都定义 | 补丁 `0004` 用 `#ifndef` 守卫 `*64` 定义 |
| 6 | `mergerfs --version` 输出 `vunknown` | codeload tag 包不含 `VERSION` 文件（release 包才带），`buildtools/update-version` 的 `cat VERSION` 失败后置为 `unknown` | 配方 `source()` 用 `save()` 生成 `VERSION=2.40.2`（不改上游脚本） |

## 源码修改

| 文件 | 原因 | 方式 | 补丁状态 |
|------|------|------|----------|
| `libfuse/lib/fuse.c` | `pthread_cancel` 未实现 | `#if HAVE_PTHREAD_CANCEL` 守卫，`#else` 分支 `pthread_detach` | ✅ `patches/0001-…patch` |
| `libfuse/lib/fuse_loop.cpp` | `pthread_setcancelstate` 未实现 | 两处调用用 `#if HAVE_PTHREAD_CANCEL` 守卫（该宏在 OHOS 未定义即省略） | ✅ 同上 |
| `libfuse/lib/cpu.cpp` | `pthread_setaffinity_np` 未实现（bionic 有 `sched_setaffinity`） | `#if HAVE_PTHREAD_SETAFFINITY_NP` 守卫，`#else` 回退 `sched_setaffinity((pid_t)(long)thread_id_,…)`；线程 pinning 为可选性能特性，构建期不经过 | ✅ `patches/0002-…patch` |
| `tests/tests.cpp` | 上游 2.40.2 的 `test_config_readdir` 仍是旧的全局枚举式 `ReadDir` API，而源码已改为 `FUSE::ReadDir`（字符串构造，合法值为 `seq`/`cosr`/`cor`）→ `make tests` 无法编译（上游 CI 只跑 `make`/`make deb`，从不构建 tests） | 仅把该用例更新到当前 API（`FUSE::ReadDir r("seq"); r.to_string(); r.from_string("cosr"); r.from_string("bogus")`），用例数不变 | ✅ `patches/0003-…patch` |
| `tools/preload.c` | `_FILE_OFFSET_BITS=64` 下 OHOS 把 `open64/openat64/fopen64/creat64` 定义为指向非 64 位函数的宏，而该文件同时定义了 32 位与 64 位两套 interposer → 重复定义 | 每个 `*64` 定义用 `#ifndef <名>` 守卫（别名宏存在时跳过） | ✅ `patches/0004-…patch` |
| `VERSION`（新增文件） | codeload tag 包不含 `VERSION`（release 包才有），`buildtools/update-version` 会退化为 `unknown` | 配方 `source()` 用 `save(... , self.version)` 生成 `VERSION=2.40.2` | 配方内生成 |

## 依赖版本

无三方依赖（vendored）。

## 测试口径

- **上游单元套件**：`tests/tests.cpp`（acutest），`make tests` 构建 `build/tests`，
  15 个用例、126 条 `TEST_CHECK` 断言；不触碰 FUSE，在 `build()` 内直接执行。
- **上游集成脚本**：`tests/TEST_*` 共 5 个，经 `tests/run-tests <挂载点>` 运行，
  依赖真实 mergerfs 挂载点 → OHOS 无可用 `/dev/fuse`，阻塞（逐条记录于
  `test_package/MANIFEST.yml`）。
- **消费者测试**：`test_package/test_mergerfs.sh`，10 项断言。

## 验证结果

```bash
# 真机 conan create（OHOS aarch64, clang 15, v2.40.2）
CREATE_RC=0

# 上游 acutest 单元套件（build() 内实跑）
Test nop...                            [ OK ]
...（共 15 个用例）
Test config...                         [ OK ]
SUCCESS: All unit tests have passed.          # 15/15 用例、126/126 断言

# 消费者（test_package/test_mergerfs.sh）
PASS: mergerfs binary is executable
PASS: preload.so installed
PASS: mergerfs.1 man page installed
PASS: mergerfs --version exit status
PASS: mergerfs --version reports 2.40.2
PASS: mergerfs --version prints ISC license
PASS: mergerfs -h exit status
PASS: mergerfs -h prints usage
PASS: mergerfs with no arguments returns non-zero
PASS: mergerfs mount attempt fails without /dev/fuse
MERGERFS_CHECK_SUMMARY checks=10 fails=0

# 产物
bin/mergerfs  lib/mergerfs/preload.so  share/man/man1/mergerfs.1  licenses/LICENSE
```

- 上游单元测试通过率：**15/15 用例（126/126 断言，100%）**。
- 上游集成脚本（`tests/TEST_*`，5 个）：**未运行**；技术原因：需要真实 mergerfs 挂载点，
  即需可访问的 `/dev/fuse`，OHOS 沙箱对 `/dev/fuse` 返回 `Permission denied`。
- 新增消费者测试：**10/10（100%）**。

## 注意事项

- 运行时挂载依赖 `/dev/fuse`。OHOS 沙箱无该设备访问权，`mergerfs <branch> <mnt>`
  会在 FUSE 层失败（权限限制，属平台限制），这也是集成脚本阻塞的原因。
- `mergerfs-fusermount` 在 Debian 上通常安装为 setuid root；Conan 打包不设 setuid，
  仅随包提供二进制。真实以 root 直接挂载不依赖它。
