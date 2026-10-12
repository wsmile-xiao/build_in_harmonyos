# mhddfs

mhddfs 是一个基于 FUSE（libfuse 2.x）的联合文件系统驱动器：把多个目录合并成一个虚拟的挂载点目录树，并在创建新文件时按各目录剩余空间自动选择落盘位置（`mlimit` 阈值）。

## 功能概述

* 合并多个目录/挂载点为一个视图：重名时先出现的目录优先
* 新文件按剩余空间选择目标目录；写入过程中空间不足时可在线迁移文件
* 覆盖常见 FUSE 回调：getattr、statfs、readdir、readlink、open、release、read、write、
  create、truncate、ftruncate、access、mkdir、rmdir、unlink、rename、utimens、chmod、
  chown、symlink、link、mknod、fsync
* 命令行：`mhddfs dir1,dir2[,...] mountpoint [-o mlimit=...,logfile=...,loglevel=...]`，
  卸载依赖 `fusermount -u <mountpoint>`

## OHOS 适配

* 构建：上游为普通 GNU Makefile（无 configure）。补丁 0001 将硬编码 `gcc` 改为 `$(CC)`
  以使用 OHOS clang 15；补丁 0003 将滞后的 VERSION 宏与发行版本 0.1.39.0 对齐。
* 链接：新增消费者侧 `src/pthread_stubs.c`（补丁 0002），为 OHOS libc 缺失的
  `pthread_cancel` / `pthread_setcancelstate` 提供 ENOSYS 语义 shim（glibc/musl 下不参与编译），
  解决静态 libfuse.a 的固定符号引用。
* xattr：OHOS sysroot 无 legacy `<attr/xattr.h>`，按上游 `WITHOUT_XATTR` 开关构建（上游将
  xattr 声明为可选组件）。
* **运行边界（重要）**：OHOS PC 当前不允许普通进程使用 FUSE 设备——`/dev/fuse` 的
  stat/open 返回 EACCES(13)、PATH 无 `fusermount`、`mount(2)` 被沙箱以 SIGSYS(31) 终止；
  内核 FUSE 能力存在但仅供系统服务使用（/proc/mounts 中媒体服务挂载
  `/data/storage/el2/media/Photo`）。因此本包交付二进制与其 CLI 契约，**真实挂载功能在当前
  平台不可用**；证据与判定树见 `knowledge/drafts/DRAFT-mhddfs-0.1.39.0-ohos-fuse-consumer-mount-boundary.*`
  与版本目录 `notes.md` / `reports/test-report.md`。

## 依赖关系

* 编译依赖：`libfuse/2.9.9`（静态库，R26；随包提供 fusermount / ulockmgr_server）、
  `uthash/2.4.0`（header-only）
* 运行依赖：具备"普通进程可用 FUSE 挂载"能力的平台（当前 OHOS PC 不满足）

## 参考资料

* 项目主页（已失效）：<http://mhddfs.uvw.ru/>
* 源码（Debian 归档 pristine orig 包）：<https://deb.debian.org/debian/pool/main/m/mhddfs/>
* 许可证：GPL-3.0-or-later
