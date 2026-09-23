# libblkid

## 简介

libblkid 是 util-linux 套件中的块设备识别库：探测块设备的文件系统/分区表/RAID 超级块（TYPE/LABEL/UUID 标签），维护 /run/blkid 缓存。fdisk、mount、e2fsprogs 等系统工具的底层依赖。

## OHOS 适配

- 构建系统：autotools（util-linux 2.42.2 官方 tarball，"单子库"模式：--disable-all-programs --enable-libblkid）
- 无外部库依赖（仅内部 libcommon；blkid.pc 无 Requires）
- 已适配版本：2.42.2（archives/l/libblkid/2.42.2）

## 依赖链

fdisk → libblkid → libuuid（libblkid 本体不依赖 libuuid，但 util-linux 同套件生态件互链）

## 上游

https://www.kernel.org/pub/linux/utils/util-linux/
