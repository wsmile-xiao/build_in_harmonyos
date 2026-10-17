# mhddfs 0.1.39.0 验证报告

## 环境

- OpenHarmony / HarmonyOS PC (HDC reported API 23) aarch64 真机，kernel 1.12.0
- clang 15.0.4（OHOS SDK）、Conan 2.29.1（OHOS 适配版）
- 本地验证 profile：`ohos-aarch64-device`（与 `ci/conan/profiles/ohos-aarch64` 同构，仅工具链路径不同）

## 数据源

- 版本：0.1.39.0（Debian 归档 pristine orig 包，上游官网失效，取证见 notes.md / PR 补充说明）
- sha256：`8bae7d3820b472cf87cd6d1fecf5d2d7965a0fe6c020b121c08c98b2c2231863`

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 手动 helper（tests/） | 7 | access.pl、seek.pl、statvfs.pl、utimes.sh、xattrs.sh、rename.c、plocks.c；均要求真实挂载 |
| Makefile 挂载类目标 | 10 | test-mount、test-umount、test、btest、tests、ptest、rename、symlinks_test、rename-test、dirtree-test（`tests` 循环调用 `test`；`rename` 仅编译 helper）；均以真实挂载为运行前提 |
| **合计** | **17** | 无自动化断言框架；全部以 live FUSE 挂载为前提 |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 上游测试（Linux+FUSE 参考环境，同源补丁构建） | **16/17 真实执行** | 新增执行 | 13 项退出码 0；`plocks/ptest`、`tests` 3 项为上游无限循环压测，按有界时间运行完成；唯一未执行 `xattrs.sh`（缺 attr/mkfs.xfs/sudo 且构建按 `WITHOUT_XATTR`）。摘要与节选：`reports/upstream-suite-linux-reference.md` |
| 上游测试（OHOS 设备逐项尝试） | 4 项设备真机执行通过 | 平台边界 | `access.pl`/`seek.pl`/`rename`/`plocks` 设备执行通过；`statvfs.pl` 缺设备 Perl 模块；其余挂载类目标 `/dev/fuse` EACCES(13)。原始输出：`reports/ohos-device-upstream-attempts.md` |
| 鸿蒙特有测试（test_package） | **10** | 新增 | `test_package/test_mhddfs.py`，T1–T10 实跑全 PASS（真实执行打包后的 `bin/mhddfs`） |
| **合计** | **16（上游参考执行）+ 10（鸿蒙消费者）** | — | 设备端另完成 4 项上游 helper 真机执行（为参考执行的可复现子集） |

## 配方验证（conan-verify，设备 profile）

```text
📋 Conan 配方验证: mhddfs 0.1.39.0
✅ G1: 配方完整性 PASS
✅ G0: 预构建风险评估 PASS（知识图谱预查询）
✅ G2: conan create（干净构建）PASS
✅ G3: 系统同名库隔离验证 (R26) PASS（纯可执行包）
✅ G4: 产物完整性 PASS
✅ 配方验证通过: mhddfs 0.1.39.0
```

- 证明：`reports/conan-verify-report.md`；conan create 完整日志保留在本地构建环境（`*.log` 按仓库规范不随 PR 提交），关键段落摘录如下：
- test_package 在 conan create 内真实执行：

```text
======== Testing the package: Executing test ========
RUN: "<venv python>" ".../test_package/test_mhddfs.py" ".../p/bin/mhddfs"
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
```

- CI 门禁脚本的 L1e 破坏性反测（R34）：移走包内 `bin/` 后重跑 `conan test` → 失败，证明测试真实依赖被测包（本地门禁日志：`mhddfs functional tests` 之前的 L1e 段，见 notes.md 验证结果）。

## FUSE 能力边界原始探测（2026-09-27，设备 currentUser）

```text
### A1. identity
HarmonyOS localhost HongMeng Kernel 1.12.0 ... aarch64 Toybox
Uid: 20020085  Gid: 20020085
CapPrm: 000000000000002a   CapEff: 000000000000002a   (无 CAP_SYS_ADMIN)

### A2. /dev/fuse node
ls: /dev/fuse: Permission denied

### A3. Python errno probes
stat  /dev/fuse: FAILED errno=13 (EACCES) Permission denied
open  /dev/fuse O_RDONLY: FAILED errno=13 (EACCES) Permission denied
open  /dev/fuse O_RDWR:   FAILED errno=13 (EACCES) Permission denied
read  /proc/filesystems:  FAILED errno=13 (EACCES) Permission denied

### A4. mount(2) syscall probe (ctypes libc.mount)
Signal 31 (core dumped)          # SIGSYS：syscall 被沙箱终止

### B1. 内核 FUSE 存在且被系统服务使用（/proc/mounts）
/dev/fuse /data/storage/el2/media/Photo fuse rw,nosuid,nodev,noexec,noatime,... user_id=0,group_id=0,default_permissions,allow_other 0 0

### B2. helper binaries
fusermount: (absent)   fusermount3: (absent)
umount: <harmonybrew>/bin/umount

### B3. libfuse 2.9.9 制品自带 fusermount 执行
<libfuse pkg>/bin/fusermount -u /tmp/mhprobe
Signal 31 (core dumped), rc=159

### C. 打包后的 mhddfs 挂载尝试（消费者可见输出）
mhddfs: directory '.../d1' added to list
mhddfs: directory '.../d2' added to list
mhddfs: mount to: .../mnt
mhddfs: move size limit 67108864 bytes
fuse: failed to open /dev/fuse: Permission denied
rc=1
```

判定树（FUSE 消费端能否在当前平台运行）：内核 FUSE 支持（系统服务在用）≠ 普通进程可挂载。
普通进程路径已被三重阻断：① `/dev/fuse` EACCES；② 无 fusermount 且自带的 fusermount 一执行
即 SIGSYS；③ `mount(2)` 直接 SIGSYS。结论：当前 OHOS PC 上用户态 FUSE 挂载不可用。

## 上游测试执行与目标平台边界（R51）

上游 17 项资产全部以 live FUSE 挂载为运行前提。目标平台 OHOS PC 内核对普通进程禁用 FUSE
（三重阻断证据见上节），因此分两路执行并如实记录：

### A. 参考环境完整执行（Linux + FUSE，同源补丁构建）

- 环境与构建：Ubuntu 22.04 / Linux 6.8；libfuse 2.9.9（本地构建静态）；系统 setuid
  `fusermount`；perl 5.34（本地 `Filesys::Statvfs 0.82`）；rsync 3.2.7；mhddfs 由与本 PR
  完全相同的 Debian orig 源码 + 3 个补丁构建（`make mhddfs WITHOUT_XATTR=1`）。
- 结果：**17 项中 16 项真实执行**（13 项退出码 0；`plocks/ptest`、`tests` 为上游无限循环
  压测，按 15s/20s 有界运行完成）；`xattrs.sh` 因缺 `attr`/`mkfs.xfs`/`sudo` 未执行。
- 关键通过证据：`test-mount` 挂载态 `df -h`/`ls mnt` 正常；`btest` 65 MiB 随机数据经 union
  写入回读**两次 md5 一致**（`d23587cfe1bf2d4306df7d327ed83bd0`）；`symlinks_test`、
  `rename-test`、`dirtree-test` 均输出 `PASSED`；`statvfs.pl`/`access.pl`/`seek.pl` 经挂载点
  执行通过。
- 摘要与原始节选：`reports/upstream-suite-linux-reference.md`（完整日志在执行机留存，未入 PR）。

### B. OHOS 设备逐项尝试（真机）

- 可独立执行通过（4 项）：`access.pl`、`seek.pl`、`rename`、`plocks`。
- 依赖缺失未执行（1 项）：`statvfs.pl`（设备 Perl 5.44 缺 `Filesys::Statvfs`）。
- 平台边界阻塞（11 项）：`utimes.sh`、`xattrs.sh` 与全部挂载类目标（test-mount/test-umount/
  test/btest/tests/ptest/symlinks_test/rename-test/dirtree-test）——`fuse: failed to open
  /dev/fuse: Permission denied`；且设备无 `fusermount`、无 pkg-config fuse。
- 原始输出与逐项分类：`reports/ohos-device-upstream-attempts.md`。

> 说明：不将参考环境结果声称为 OHOS 目标平台结果；目标平台的挂载运行受平台边界限制，
> 已在 PR 与知识草稿中如实标注。设备侧不含伪造挂载或 skip 美化。

## 结论

- 编译与交付：**PASS**（conan-verify G0–G4；包内含 bin/mhddfs、man 页、许可证）
- 消费者测试：**10/10 PASS**（鸿蒙特有测试行 = 10）
- 上游测试：**16/17 真实执行**（Linux+FUSE 参考环境，同源补丁构建；13 项退出码 0，
  `plocks/ptest`、`tests` 有界压测运行完成，`xattrs.sh` 1 项未执行）；设备端 4 项 helper
  真机执行通过，其余受 `/dev/fuse` EACCES(13) 平台边界阻塞
- 挂载功能：**BLOCKED（平台边界）**（/dev/fuse EACCES、无 fusermount、mount(2) SIGSYS；
  内核 FUSE 仅系统服务可用）——如实标注，不含伪造
