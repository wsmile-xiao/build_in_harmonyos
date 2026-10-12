# 上游测试套件执行报告（Linux + FUSE 参考环境）

> 目的：上游 mhddfs 的测试资产全部以 **live FUSE 挂载**为前提；目标平台 OHOS PC 的内核对
> 普通进程禁用 FUSE（原始证据见 `ohos-device-upstream-attempts.md`）。本报告记录在与本 PR
> **同源（同一 Debian orig 压缩包 + 同一 3 个补丁）** 构建的 Linux+FUSE 参考环境上完整执行
> 上游测试套件的结果与原始输出，供核验。

## 1. 环境与可复现构建

| 项 | 值 |
|---|---|
| 主机 | Ubuntu 22.04 / Linux 6.8.0-40-generic x86_64 |
| 源码 | `https://deb.debian.org/debian/pool/main/m/mhddfs/mhddfs_0.1.39.0.orig.tar.xz`，sha256 `8bae7d3820b472cf87cd6d1fecf5d2d7965a0fe6c020b121c08c98b2c2231863` |
| 补丁 | `patches/0001-Makefile.patch`、`patches/0002-src-pthread_stubs.c.patch`、`patches/0003-src-version.h.patch`（与本 PR 完全一致） |
| 构建依赖 | libfuse 2.9.9（Debian orig `fuse_2.9.9.orig.tar.gz`，`./configure --disable-example --disable-util --disable-shared --enable-static && make && make install`）、uthash 2.4.0 头文件（来自本仓 conan 制品包） |
| mhddfs 构建命令 | `PKG_CONFIG_PATH=<fuse-prefix>/lib/pkgconfig make -j4 mhddfs WITHOUT_XATTR=1`（与配方一致的 `-DFUSE_USE_VERSION=26 -DWITHOUT_XATTR` 语义） |
| 二进制 | `mhddfs version: 0.1.39.0` |
| 运行时 | FUSE 2.9.9；系统 setuid `fusermount`（`/usr/bin/fusermount -> fusermount3`）；perl 5.34.0（本地安装 `Filesys::Statvfs 0.82`）；rsync 3.2.7 |

## 2. 执行结果（17 项上游资产）

| # | 上游资产 | 执行方式 | 结果 |
|---|----------|----------|------|
| 1 | tests/access.pl | `perl tests/access.pl mnt mnt/afile.txt`（挂载点内） | ✅ exit 0（R/W/X 打印正常） |
| 2 | tests/seek.pl | `perl tests/seek.pl mnt/seek-test.bin` | ✅ exit 0（seek 后写入，md5 输出 `32e93defc62c0049dcacbf25691ada5a`） |
| 3 | tests/statvfs.pl | `perl tests/statvfs.pl mnt` | ✅ exit 0（输出 statvfs 聚合表） |
| 4 | tests/utimes.sh | `make symlinks_test` | ✅ exit 0，输出 `**************** PASSED ******************` |
| 5 | tests/xattrs.sh | `bash tests/xattrs.sh` | ❌ 未执行：脚本前置要求 `attr` CLI + `mkfs.xfs` + `sudo mount -o loop`；参考环境无这些工具且无免密 sudo；且本适配按 `WITHOUT_XATTR` 构建（上游将 xattr 声明为可选）。输出：`Need attr command to test extended attributes` |
| 6 | tests/rename.c | `make rename` + `./rename mnt/from.txt mnt/to.txt` | ✅ exit 0（mnt 内改名成功，`to.txt` 存在） |
| 7 | tests/plocks.c | `make ptest`（有界 15s） | ✅ 编译并运行：两线程 rwlock 循环无死锁/崩溃，15s 后有界终止（上游该目标本身为无限压测） |
| 8 | make test-mount | 原目标（mhddfs 后台挂载 + `df -h test1 test2; ls mnt`） | ✅ exit 0（`/dev/sda2` 汇总行 + `ls mnt` 输出；`/proc/mounts` 可见 `fuse.mhddfs`） |
| 9 | make test-umount | 原目标（`fusermount -u mnt`） | ✅ exit 0，卸载成功（`(unmounted)`） |
| 10 | make test（1 MiB 写入） | 挂载态执行原目标 | ✅ exit 0（`mnt/file_EIVxSiu0i6` 通过 union 写入） |
| 11 | make btest（65 MiB 写读 + md5） | 挂载态执行原目标 | ✅ exit 0，两次 md5 一致：`d23587cfe1bf2d4306df7d327ed83bd0`（tee 流 / union 回读） |
| 12 | make tests | 原目标（无限循环 `make test`）有界 20s | ✅ 循环持续通过并写入 union；20s 有界终止（124） |
| 13 | make ptest | 同 #7（原目标有界 15s） | ✅ 同上 |
| 14 | make rename | 原目标（编译 helper） | ✅ exit 0 |
| 15 | make symlinks_test | 原目标（内部自挂载） | ✅ 同 #4 |
| 16 | make rename-test | 原目标（自挂载 + mv 断言 + 卸载） | ✅ exit 0，`******************** PASSED ***********************` |
| 17 | make dirtree-test | 原目标（自挂载 + 目录树断言 6 项 + 卸载） | ✅ exit 0，`******************** PASSED ***********************` |

统计：**17 项中 16 项真实执行**（13 项退出码 0；`plocks/ptest`、`tests` 为上游无限循环压测，
按有界时间运行完成），**1 项（xattrs.sh）因外部工具链缺失未执行**（具体原因见上表 #5）。

## 3. 关键原始输出（节选）

```text
##### make test-mount #####
./mhddfs test1 test2 mnt -o logfile=logfile.log,mlimit=50m,nonempty,loglevel=0
mhddfs: directory '.../test1' added to list
mhddfs: directory '.../test2' added to list
mhddfs: mount to: .../mnt
df -h test1 test2
Filesystem      Size  Used Avail Use% Mounted on
/dev/sda2       1.8T  164G  1.5T  10% /
ls mnt
to.txt
<<< exit=0
/proc/mounts: .../test1;.../test2 on .../mnt type fuse.mhddfs (rw,nosuid,nodev,relatime,user_id=1000,group_id=1000)

##### make btest（65 MiB 随机数据经 union 写入并回读） #####
mnt/file_czEOnLME9X
d23587cfe1bf2d4306df7d327ed83bd0  -
d23587cfe1bf2d4306df7d327ed83bd0  mnt/file_czEOnLME9X
<<< exit=0

##### make rename-test #####
touch rename-test/mnt/test-file ; mv rename-test/mnt/test-file rename-test/mnt/test-file.1
mkdir rename-test/mnt/test-dir ; mv ... ; mv rename-test/mnt/test-dir.2/123 rename-test/mnt/test-dir.3
fusermount -u rename-test/mnt
******************** PASSED ***********************

##### make dirtree-test #####
bash -c 'touch dirtree-test/1/{1,2,3,4} dirtree-test/2/{3,4,5,6}'
test `find dirtree-test/mnt -type f | sort -u |wc -l` -eq 6
test -e dirtree-test/mnt/1 ... test -e dirtree-test/mnt/6
******************** PASSED ***********************

##### tests/xattrs.sh（唯一未执行项的原因） #####
+ which attr
+ echo 'Need attr command to test extended attributes'
Need attr command to test extended attributes
+ exit 1
```

## 4. 范围与限制

- 本报告执行于 **Linux+FUSE 参考环境**（同源补丁构建），用于证明上游测试在具备 live FUSE
  的环境中真实通过；**不将参考环境结果声称为 OHOS 目标平台结果**。目标平台 OHOS PC 的
  逐项尝试与平台边界见 `ohos-device-upstream-attempts.md`。
- 完整套件原始日志（含 FUSE 调试输出，约 55 MB）保留在执行机上，未随 PR 提交；本报告的
  摘要与节选来自该日志，可依据第 1 节命令在任何具备 FUSE 的 Linux 上复现。
