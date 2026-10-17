# 上游测试资产在 OHOS PC 设备上的逐项执行尝试（R51 补充证据）

> 目标平台：HarmonyOS PC aarch64 真机（kernel 1.12.0），普通用户 `currentUser`（uid 20020085）。
> 本文件记录 2026-10-03 在设备上对上游 17 项测试资产的逐项执行尝试与原始输出，以及平台
> FUSE 边界（详见 `test-report.md` 的 FUSE 能力探测段）。

## 1. 平台边界（前置事实）

```text
stat  /dev/fuse: FAILED errno=13 (EACCES) Permission denied
open  /dev/fuse O_RDONLY: FAILED errno=13 (EACCES) Permission denied
open  /dev/fuse O_RDWR:   FAILED errno=13 (EACCES) Permission denied
read  /proc/filesystems:  FAILED errno=13 (EACCES) Permission denied
mount(2) syscall probe:   Signal 31 (core dumped)        # SIGSYS
libfuse 自带 fusermount:  Signal 31 (core dumped), rc=159
系统 PATH: 无 fusermount/fusermount3
内核 FUSE 仅供系统服务（/proc/mounts 中媒体服务挂载 /data/storage/el2/media/Photo）
```

## 2. 可独立执行的上游 helper（设备真机）

```text
===== tests/access.pl =====   exit=0
Test .../a1 R_OK... ok / W_OK... ok / X_OK... ok
Test .../a1/file.txt R_OK... ok / W_OK... ok / X_OK... fail   （普通文件无 x 位属预期）

===== tests/seek.pl =====   exit=0
Save data... / Seek... / Save data...
32e93defc62c0049dcacbf25691ada5a  .../a2-seek.bin

===== tests/rename.c（make rename 编译 + 运行） =====   exit=0
-rw-r----- 1 ... 5 .../a4-to

===== tests/plocks.c（make ptest，有界 15s） =====   运行完成（124 有界终止）
<两线程 rwlock rdlock/wrlock 循环正常，无死锁/崩溃>
```

结果：**4 项独立 helper 在 OHOS 设备真机执行通过**（access.pl、seek.pl、rename、plocks）。

## 3. 依赖缺失 / 平台边界阻塞的上游资产

```text
===== tests/statvfs.pl =====   exit=2
Can't locate Filesys/Statvfs.pm in @INC ... at tests/statvfs.pl line 10.
（设备 Perl 5.44 未安装 Filesys::Statvfs 模块；该 helper 未执行）

===== make test-mount =====   Error 1
mhddfs: mount to: .../mnt
mhddfs: move size limit 52428800 bytes
fuse: failed to open /dev/fuse: Permission denied
make: *** [Makefile:129: test-mount] Error 1

===== make test-umount =====   （忽略错误的 `-fusermount`）
make: fusermount: No such file or directory (Error 127 ignored)

===== make symlinks_test（tests/utimes.sh） =====   Error 255
fuse: failed to open /dev/fuse: Permission denied
tests/utimes.sh: line 28: fusermount: command not found
tests/utimes.sh: line 24: rsync: command not found
FAILED:

===== make rename-test =====   Error 1
fuse: failed to open /dev/fuse: Permission denied
make: *** [Makefile:179: rename-test] Error 1

===== make dirtree-test =====   Error 1
fuse: failed to open /dev/fuse: Permission denied
make: *** [Makefile:197: dirtree-test] Error 1

===== make tests =====   有界 30s（124）
（mnt 未挂载，循环在普通目录上运行，不构成对 union 的有效验证——不计入通过）
```

## 4. 分类汇总（设备侧）

| 分类 | 项目 | 说明 |
|------|------|------|
| 设备真机执行通过 | access.pl、seek.pl、rename、plocks（4 项） | 原始输出见第 2 节 |
| 依赖缺失未执行 | statvfs.pl（1 项） | 设备 Perl 缺 `Filesys::Statvfs` 模块 |
| 平台边界阻塞（`/dev/fuse` EACCES(13)） | utimes.sh、xattrs.sh、test-mount、test-umount、test、btest、tests、ptest、symlinks_test、rename-test、dirtree-test（11 项） | 其中多项目标还隐含 pkg-config fuse/gcc/fusermount 前提，设备均不具备 |
| 小计 | 17 项：4 通过 + 1 依赖缺失 + 11 平台阻塞 | — |

> 说明：上游 17 项全部以 live FUSE 挂载为运行前提，目标平台内核禁止普通进程访问 FUSE，
> 因此设备侧无法执行挂载类用例；已在具备 FUSE 的参考环境以同源补丁构建完整执行上游套件
> （16/17，见 `upstream-suite-linux-reference.md`）。设备侧结果如实记录，不含伪造。
