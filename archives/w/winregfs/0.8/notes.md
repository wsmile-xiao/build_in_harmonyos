# winregfs 0.8 适配笔记

## 基本信息

- 上游：https://codeberg.org/jbruchon/winregfs （Windows Registry FUSE filesystem，Jody Bruchon）
- 版本：v0.8（tag `v0.8`，2021-09-15）
- 源码包：`https://codeberg.org/jbruchon/winregfs/archive/v0.8.tar.gz`
- SHA-256：`de53ba04050edb45d0b8f9c485bf72502f1782a32ba672a9d8290dbd43aad299`（≥2 次下载一致）
- 构建系统：**plain Makefile**（无 configure、无 CMake）
- 编译器：clang 15（OHOS aarch64）
- 产物：`mount.winregfs`、`fsck.winregfs`（命令行工具）

## 依赖

| 依赖 | 类型 | 说明 |
|------|------|------|
| libfuse/2.9.9 | 强制第三方 | winregfs 使用 FUSE 2.x API（`FUSE_USE_VERSION 26`、`#include <fuse.h>`），与 libfuse 3.x 不兼容 |

W0 核验（干净 conan 缓存真实拉取，非本地缓存命中）：

```bash
$ conan download libfuse/2.9.9 -r=ohpcd
Connecting to remote 'ohpcd' anonymously
Downloading recipe 'libfuse/2.9.9#bc32f257e37c6598525028a2cc4e6da4'
Downloading 'libfuse/2.9.9' sources
Downloading package 'libfuse/2.9.9#...:21b17f8b2bc0e9511e276e3d57a23893067cefe5#833a170f...'
libfuse/2.9.9: Package installed 21b17f8b2bc0e9511e276e3d57a23893067cefe5
Download completed in 31s
```

结论：唯一强制第三方依赖 `libfuse/2.9.9` **可消费**（recipe + 二进制包均在制品仓）。

## 上游测试情况（清点结论）

**上游 v0.8 没有自动化测试套件**：

- 源码包根目录仅 21 个文件，无 `tests/`、无 `*.test`、无 `check`/`spec` 相关文件；
- Makefile 只有 `all` / `install` / `package` / `clean` / `distclean` 目标，**无 `make check` / `make test`**；
- 无 ctest / pytest / meson test 注册；
- `chroot_build.sh` 只是打包脚本，不是测试。

因此没有“上游样例”可跑；上游提供的**真实测试入口**是随包的两个二进制：

```bash
fsck.winregfs [-v] <hive>            # 遍历 hive 全部键/值并报告错误（可脚本断言退出码）
mount.winregfs [-o ro] <hive> <mnt>  # FUSE 挂载（需 /dev/fuse + root，容器/CI 内不可用）
```

本次适配用**自建的真实 hive 样本**驱动这些入口（见 test_package/mkhive.py）。

## 构建步骤

```bash
# 1. 取源码
curl -L -o winregfs-v0.8.tar.gz https://codeberg.org/jbruchon/winregfs/archive/v0.8.tar.gz
sha256sum winregfs-v0.8.tar.gz   # de53ba04...aad299

# 2. 编译（注入 FUSE 路径与 OHOS pthread 兼容开关）
make CC=clang -j1 \
  FUSE_CFLAGS="-I<libfuse>/include -I<libfuse>/include/fuse" \
  FUSE_LDFLAGS="-L<libfuse>/lib" \
  BUILD_PTHREAD_COMPAT=1
# → mount.winregfs, fsck.winregfs, mount.winregfs.8.gz, fsck.winregfs.8.gz
```

## 遇到的问题与解决方案

| # | 问题（首个真实错误） | 根因 | 解决方案 |
|---|----------------------|------|----------|
| 1 | `winregfs.h:15:10: fatal error: 'fuse.h' file not found` | OHOS 的 libfuse 包**不含 `fuse.pc`**，上游 `pkg-config fuse --cflags` 返回空 → 无 `-I` 路径 | 补丁 0001：Makefile 的 `FUSE_CFLAGS`/`FUSE_LDFLAGS` 改为 `?=` 可覆盖，由配方注入 Conan 依赖路径 |
| 2 | `ld.lld: error: undefined symbol: pthread_cancel`（`fuse.o:(fuse_stop_cleanup_thread)`、`fuse_loop_mt.o:(fuse_session_loop_mt)`，来自 `libfuse.a`） | OHOS musl `libc.so` 导出 101 个 `pthread_*`，但**不导出**线程取消族（`pthread_cancel`/`pthread_setcancelstate`/`pthread_setcanceltype`/`pthread_testcancel`）；`libc.a` 里有而 `libc.so` 没有。winregfs 自身只用 mutex，不调用取消 | 补丁 0002：新增 `pthread_compat.c` 提供这 4 个符号（尽力而为的 no-op，OHOS 不实现异步取消），Makefile 增加 `BUILD_PTHREAD_COMPAT=1` 挂钩按需链接。对应知识库 **E085** |
| 3 | `make: jobserver mkfifo: /storage/.../GMfifo...: Operation not permitted` | 本机 HMDFS 不允许 make 创建 jobserver FIFO | 固定 `-j1`（R9） |

## 源码修改

两个补丁（均 `patch_type: portability`，不含平台宏）：

- `patches/0001-Makefile.patch`：`FUSE_CFLAGS/FUSE_LDFLAGS` 改为可覆盖（`?=`，并加 `2>/dev/null`），新增 `BUILD_PTHREAD_COMPAT ?= 0` 与 `OBJS_MOUNT+=pthread_compat.o` 条件挂钩。
- `patches/0002-pthread_compat.c.patch`：新增 `pthread_compat.c`（47 行，4 个函数 + 说明为什么 OHOS 上安全）。

可复现性校验：`orig + 两个补丁 == work`（`diff -r` 逐字节一致，仅构建产物差异）。

## 上游测试执行结果

测试入口：`fsck.winregfs -v <hive>`（上游无自动化测试套件，无可逐项列出的上游用例）。

真实 hive 样本（`test_package/mkhive.py` 生成，8192 字节 / 2 页）：

```
\ROOT
  Version  REG_DWORD = 0x123
  \Test
    Path   REG_SZ    = "OHOS"
    Count  REG_DWORD = 7
```

| 场景 | 命令 | 结果 | 退出码 |
|------|------|------|--------|
| 合法 hive | `fsck.winregfs -v good.hiv` | `Keys: 2   Values: 3   Max key depth: 1` / `Hive good.hiv is clean.` | 0 |
| 损坏 hive（magic 改 `XXXX`） | `fsck.winregfs -v bad.hiv` | `Path traversal errors: 1` / `Hive bad.hiv has 1 total errors` | 1 |
| 无参数 | `fsck.winregfs` | 打印 Usage | 1 |
| 版本 | `mount.winregfs -V` | `Windows Registry Filesystem 0.8 (2021-09.15)` | 0 |

注：`mount.winregfs` 的实际挂载需要 `/dev/fuse` 与 root，本机 `/dev/fuse` 不可访问（容器/设备限制），故挂载路径未做端到端验证。

## 交付物

| 文件 | 说明 |
|------|------|
| `bin/mount.winregfs` | FUSE 挂载工具 |
| `bin/fsck.winregfs` | hive 完整性检查工具 |
| `share/man/man8/*.8.gz` | 两个工具的 man page |

## 注意事项

- `fsck.winregfs <hive>`（单个参数）会正常执行完整检查；上游 `argc == 2 && !strcaseeq(argv[1], "-v")` 分支只在唯一参数**恰为 `-v`** 时触发（`strcaseeq` 语义同 `strcmp`，相等返回 0），此时仅打印 banner 并返回 0。这是上游行为，本适配不改。
- OHOS 不实现异步线程取消，`pthread_compat.c` 的取消函数是 no-op；winregfs 自身不使用取消，libfuse 的取消仅在其多线程循环收尾路径出现，不影响本工具的实际使用。
---

**编译结束**: 2026-10-03 13:20
**最终状态**: built
