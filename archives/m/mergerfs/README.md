# mergerfs — FUSE 联合文件系统

`mergerfs` 是一个基于 FUSE 的联合文件系统：把多个目录（**branches**）合并成
一个挂载点，面向 JBOD 场景，支持按需选择文件放置与读取策略（如 `mfs`、`epmfs`、
`rand`、`pfrd` 等），并在 branch 之间动态地分散/聚合文件。

## 主要功能

- 将多个目录合并为单一挂载点（union / JBOD）。
- 可配置的 `func.<FUNC>=<POLICY>` 策略：创建、搜索、读写走哪个 branch。
- 支持符号链接、xattr、`moveonenospc`、`minfreespace`、`statfs` 语义等。
- 提供 `mergerfs-fusermount` 与 `mount.mergerfs` 辅助工具。

## OHOS 适配要点

- **自包含源码**：上游 2.40.2 官方包自带 vendored libfuse 2.x fork 以及
  wyhash / ghc::filesystem / fmt / optional-lite / concurrentqueue，**无外部依赖**，
  纯 `make` 构建。
- **线程取消**：OHOS bionic 未实现 `pthread_cancel`/`pthread_setcancelstate`；
  vendored libfuse 中这两处调用用 `HAVE_PTHREAD_CANCEL` 特性宏守卫。
- **librt**：OHOS 把 librt 并入 libc，上游固定的 `-lrt` 用命令行 `LDFLAGS` 覆盖去除。
- **测试**：上游 acutest 单元套件在构建期实跑；`tests/TEST_*` 集成脚本需要真实
  mergerfs 挂载点（`/dev/fuse`），OHOS 沙箱不可访问，如实记录为阻塞。

## 产物

| 路径 | 说明 |
|------|------|
| `bin/mergerfs` | 主程序 |
| `lib/mergerfs/preload.so` | LD_PRELOAD 辅助库 |
| `share/man/man1/mergerfs.1` | 手册页 |

> `mergerfs-fusermount` / `mount.mergerfs` 由 vendored libfuse 的 Makefile 按
> `uname -s == Linux` 条件构建；OHOS 上 `uname -s` 非 `Linux`，因此不产出这两个辅助
> 程序（核心 `mergerfs` 不依赖它们）。

## 参考资料

- 上游仓库：<https://github.com/trapexit/mergerfs>
- 许可证：ISC
