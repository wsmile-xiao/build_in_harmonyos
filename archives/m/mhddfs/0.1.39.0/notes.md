# mhddfs 0.1.39.0 适配笔记

## 编译环境
- 构建系统: makefile（上游普通 GNU Makefile，无 configure）
- 编译日期: 2026-09-27
- 编译器: OHOS clang 15.0.4（aarch64-unknown-linux-ohos）
- 状态: built

## 源码与版本口径
- 上游官网 http://mhddfs.uvw.ru/ 已失效（http 拒连、https 证书不匹配，2026-09-27 实测），
  svn.uvw.ru 同步消失；唯一权威可得的 pristine 源码是 Debian 归档 orig 包
  `mhddfs_0.1.39.0.orig.tar.xz`（不含 Debian 补丁，Debian 补丁在单独的 .debian.tar.xz），
  sha256 `8bae7d3820b472cf87cd6d1fecf5d2d7965a0fe6c020b121c08c98b2c2231863` 与下载件一致。
- 上游 `src/version.h` 的 VERSION 宏滞后为 "0.1.39"，与发行/包版本 0.1.39.0 不一致；
  补丁 0003 将其对齐为 "0.1.39.0"（Debian 官方构建经 changelog→update_version 注入同一值）。
  `mhddfs --version` 现输出 `mhddfs version: 0.1.39.0`。

## 编译步骤

```bash
make -j1 mhddfs \
  CC=<OHOS clang> \
  CFLAGS="-Wall -O2 -I<libfuse>/include -I<libfuse>/include/fuse -I<uthash>/include \
          -DFUSE_USE_VERSION=26 -MMD -DWITHOUT_XATTR -D_FILE_OFFSET_BITS=64" \
  LDFLAGS="-L<libfuse>/lib -lfuse -lulockmgr -lpthread"
```

由 conanfile.py `build()` 从依赖 cpp_info 自动组装 include/lib 路径；显式指定
`make mhddfs` 直接构建目标，绕过默认 `all` 目标中依赖 debian/changelog 的
`update_version` 分支（原包无 debian/ 目录，直接 `make` 会用空 DEBVERSION 覆写 version.h）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 编译使用主机 `gcc`，无法交叉编译 | 上游 Makefile 的编译/链接规则硬编码 `gcc`，不读取 `$(CC)` | 补丁 0001：两行规则 `gcc` → `$(CC)` |
| 2 | `#include <attr/xattr.h>` 找不到 | xattr 代码包含 legacy libattr 头；OHOS sysroot 只有 `<sys/xattr.h>` | 使用上游自带 `WITHOUT_XATTR` 编译开关（README 声明 xattr 为可选组件），传入 `-DWITHOUT_XATTR`，无源码改动 |
| 3 | 静态链接失败 `undefined symbol: pthread_cancel / pthread_setcancelstate` | OHOS libc 未实现 pthread 取消族函数（E051）；libfuse 2.9.9 的 `fuse.c`/`fuse_loop_mt.c` 无条件引用这两个符号 | 新增消费者侧 shim `src/pthread_stubs.c`（补丁 0002，与 libfuse 2.9.9 test_package 同型；返回 ENOSYS 语义；glibc/musl 守卫下不生效）。默认单线程 `fuse_main()` 流程不触达这两个调用点 |
| 4 | 直接 `make` 会改写 version.h 为且 sleep 5s | 原包无 debian/changelog，`DEBVERSION` 为空且 ≠ `VERSION`，触发 `update_version` 分支 | 构建调用明确目标 `make mhddfs`，不进入该分支 |
| 5 | 运行挂载失败 `fuse: failed to open /dev/fuse: Permission denied` | OHOS PC 不允许普通进程访问 FUSE 设备：`/dev/fuse` stat/open 均 EACCES(13)，PATH 无 fusermount，`mount(2)` 被沙箱以 SIGSYS(31) 终止；内核 FUSE 仅系统服务在用（/proc/mounts 中媒体服务挂载 /data/storage/el2/media/Photo） | 平台边界，如实记录（reports/test-report.md 原始证据 + 知识草稿）；消费者测试改为 CLI 契约 + 有界挂载尝试（真实执行 bin/mhddfs） |

## 源码修改

| 文件 | 修改 | 机制 |
|------|------|------|
| Makefile | 编译/链接规则 `gcc` → `$(CC)`（2 行） | patches/0001-Makefile.patch |
| src/pthread_stubs.c | 新增：pthread_cancel / pthread_setcancelstate 的 ENOSYS shim（glibc/musl 守卫） | patches/0002-src-pthread_stubs.c.patch |
| src/version.h | `VERSION "0.1.39"` → `"0.1.39.0"` | patches/0003-src-version.h.patch |

## 依赖版本

- libfuse/2.9.9（制品仓预编译静态库，R26；同时提供 fusermount / ulockmgr_server）
- uthash/2.4.0（header-only）
- 运行期额外需要"普通进程可用的 FUSE 挂载能力"，本平台当前不满足（见问题 5）

## 验证结果

```bash
# 配方验证（设备 profile：ohos-aarch64-device）
python3 scripts/ohc-run.py conan-verify mhddfs 0.1.39.0 --profile ohos-aarch64-device
# → G0/G1/G2/G3/G4 全 PASS；conan create 成功

# 消费者测试（conan create 的 test_package 阶段实跑）
#   RUN: python3 test_mhddfs.py <pkg>/bin/mhddfs
PASS  T1 --version prints the packaged release and exits 0
PASS  T2 -V prints the packaged release and exits 0
PASS  T3 no arguments prints usage and exits non-zero
PASS  T4 a single directory prints usage and exits non-zero
PASS  T5 a nonexistent source directory is rejected with a diagnostic
PASS  T6 a non-directory source argument is rejected with a diagnostic
PASS  T7 duplicate source directories are eliminated at startup
PASS  T8 mlimit=64m is parsed into 64 MiB
PASS  T9 startup reports the merged directory list and the mount point
PASS  T10 real mount attempt fails cleanly with a FUSE diagnostic
mhddfs functional tests: 10/10 passed

# 版本输出
$ mhddfs --version
mhddfs version: 0.1.39.0
```

## 发现与知识

- ✅ 上游 Makefile 编译/链接规则硬编码 gcc，交叉编译必须改为 $(CC)（构建性，补丁 0001）
- ✅ OHOS sysroot 无 legacy <attr/xattr.h>，上游 WITHOUT_XATTR 编译开关是 xattr 可选组件的正路
- ✅ OHOS libc 缺 pthread_cancel/pthread_setcancelstate：静态 libfuse.a 消费端需要消费者侧 ENOSYS shim（补丁 0002）
- ✅ OHOS PC 普通进程无法使用 FUSE：/dev/fuse EACCES、无 fusermount、mount(2) SIGSYS（ref: DRAFT-mhddfs-0.1.39.0-ohos-fuse-consumer-mount-boundary）
- ✅ 无法真实挂载时 FUSE 消费端测试按 CLI 契约 + 有界挂载双向判定构造（ref: DRAFT-mhddfs-0.1.39.0-fuse-consumer-test-construction）

## 上游测试用例申报（R51）

- 上游测试资产：`tests/` 7 个 helper 文件（access.pl、seek.pl、statvfs.pl、utimes.sh、
  xattrs.sh、rename.c、plocks.c）+ Makefile 挂载类目标 10 个（test-mount、test-umount、
  test、btest、tests、ptest、rename、symlinks_test、rename-test、dirtree-test；其中 `tests`
  循环调用 `test`，`rename` 仅编译 helper）；合计 17 项，均以**真实 FUSE 挂载**为运行前提。
- 真实执行（参考环境）：在与本 PR 同源补丁构建的 Linux+FUSE 参考环境完整执行上游套件，
  17 项中 16 项真实执行（13 项退出码 0；`plocks/ptest`、`tests` 为上游无限循环压测，按
  15s/20s 有界运行完成）；`xattrs.sh` 因缺 `attr`/`mkfs.xfs`/`sudo` 且构建按 `WITHOUT_XATTR`
  未启用 xattr 而未执行。摘要与节选见 `reports/upstream-suite-linux-reference.md`。
- 目标平台（OHOS PC）：设备真机逐项尝试——`access.pl`、`seek.pl`、`rename`、`plocks`
  4 项独立 helper 执行通过；`statvfs.pl` 因设备 Perl 缺 `Filesys::Statvfs` 模块未执行；
  其余挂载类目标因 `/dev/fuse` EACCES(13) 平台边界阻塞（原始输出见
  `reports/ohos-device-upstream-attempts.md`）。
- 适配后消费者测试：`test_package/test_mhddfs.py` 10 项断言全部通过（鸿蒙特有测试行 = 10）。

## 注意事项

- 本包交付：`bin/mhddfs` + man 页 + 许可证；二进制可运行、CLI 契约完整。
- **挂载功能受平台边界限制**：OHOS PC 当前不允许普通进程使用 FUSE 设备，真实挂载不可用；
  PR 中如实标注，不宣称可挂载，不伪造挂载结果。内核 FUSE 能力存在（系统媒体服务在用），
  未来平台开放该能力后本包即可直接使用。
- `-o remember=N` 的 LRU prune 线程与多线程 loop 在 OHOS 上依赖 pthread 取消族函数
  （shim 返回 ENOSYS），默认单线程流程不受影响；详见知识草稿。
- 源码 URL 使用 Debian 归档 pristine orig（上游官网失效），PR 补充说明中有完整取证。

## 对话记录

### 对话 #1 — 2026-09-27 适配会话（简录）

- 人类：下达 mhddfs 0.1.39.0 任务（#8851 / feat/mhddfs-0.1.39.0），要求路径 A+B 交付、真机验证、如实记录。
- AI：W0 依赖检查（libfuse/2.9.9 与 uthash 已发布；上游官网 mhddfs.uvw.ru 实测失效）；W1 创建隔离 worktree（基于 main c611f7d61）。
- AI：获取 Debian orig 源码（sha256 8bae7d… 复核一致）；lang-preflight 通过（detected=c，属 cpp 兼容族）。
- AI：真机 FUSE 能力探针 → /dev/fuse EACCES(13)、无 fusermount、mount(2) SIGSYS(31)；确定"可构建交付 + 平台边界如实记录"路线。
- AI：适配（3 个补丁）→ 手动构建通过 → mhddfs --version 输出 0.1.39.0 → conan-verify G0–G4 PASS → 本地 CI 门禁 100%（含 L1e 反测）。
- AI：沉淀 2 条知识草稿（FUSE 消费端挂载边界 / 测试构造）并过 draft-review；消费者测试 10/10（真实执行 bin/mhddfs）。

---
**编译结束**: 2026-09-27
**最终状态**: built
