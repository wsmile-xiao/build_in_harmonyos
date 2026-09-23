# cramfsswap

cramfs 文件系统镜像小端/大端字节序互换工具：读取 cramfs 镜像，把 superblock、
inode（mode/uid/size/gid/namelen/offset 位域）、块指针逐字段做字节交换，
输出对端字节序镜像并按 zlib crc32 重算镜像 CRC。GPL-2.0-or-later。

- 上游：Debian native 包（无独立上游 tarball），Vcs 即 salsa：
  https://salsa.debian.org/debian/cramfsswap
- 用法：`cramfsswap <in> <out>`（交换两次即复原；`--version`/`--help` 为
  OHOS 适配新增的自报入口）
- 依赖：仅 zlib（CRC32），OHOS 侧由 conan zlib/1.3.1.1 静态链接进产物。

## OHOS 适配要点（跨版本通用）

- 手写 Makefile（非 autotools）：`CC`/`LD`/`CPPFLAGS`/`LDFLAGS` 全部可由
  make 命令行变量覆盖；OHOS 无裸 `cc`，`CC`/`LD` 必须同时覆盖。
- `linux/cramfs_fs.h` 与 `byteswap.h` 由 OHOS NDK sysroot 直接提供；
  `CRAMFS_MAGIC` 在 `linux/magic.h`（被前者传递 include）。
- 上游唯一测试为 debian autopkgtest test-cmd（mkfs.cramfs 夹具）；OHOS CI
  无 util-linux 的 mkfs.cramfs，test_package 用确定性 Python 构造镜像运行
  同一「首换不同/再换复原」断言。
- 上游无版本探针：CI L2 冒烟探测需要 `--version`/`-V`/`--help`/`-h` 返回 0，
  适配补丁新增这些入口。

## 版本

| 版本 | 状态 | 备注 |
| --- | --- | --- |
| 1.4.5 | built | 首个移植版本（2026-09-21） |
