# libatasmart

## 简介
libatasmart 是 Linux 下 ATA S.M.A.R.T. 磁盘健康信息读取与报告库
(纯 C,LGPL),曾是 systemd/udisks 生态的 SMART 后端,提供 SkDisk API
与 skdump/sktest 诊断工具。

## OHOS 适配
- **构建系统**: autotools(tarball 自带 configure)
- **依赖链**: 无(纯 libc;ATA passthrough 经内核 ioctl)
- **上游仓库**: http://git.0pointer.net/git/libatasmart.git(Debian snapshot 归档取源)
- **已知交叉坑**: 构建期 strpool host 工具需跳过(补丁 0001,tarball 自带生成产物)
- **版本索引**:
  - 0.19 — 2026-09-28 适配(Debian orig tar.xz,零依赖,标准 autotools)
