# libbtrfs-dev 6.2

- 上游坐标：`kdave/btrfs-progs` tag `v6.2`；源码归档 SHA-256 见 `conandata.yml`。
- 包含上游 `libbtrfs` 公共头文件、btrfs kernel/UAPI 头文件闭包及 `libbtrfs` shared 或 static library。
- 上游 `libbtrfs` 由 `kernel-lib/rbtree.c`、`libbtrfs/send-stream.c`、`send-utils.c`、`crc32c.c` 四个对象组成。配方直接构建这些上游对象，不配置与开发库无关的工具程序及其可选依赖。
- HarmonyOS PC 消费者测试分别检查安装头文件闭包/链接符号，以及 AArch64 LP64 和 ioctl 结构布局。
- 不安装 `libbtrfsutil/btrfs_tree.h` 与其配套 `btrfs.h`：该 UAPI 头和旧版 libbtrfs 的 `ioctl.h` 定义了重复的 ioctl 结构，不能作为同一 include 闭包公开。
- ioctl 的功能行为依赖 btrfs 内核文件系统能力；本包测试不声称验证实际挂载或 ioctl 操作。

## 上游 161 项 `tests/**/test.sh` 真机实跑（2026-10-03）

- 分母口径：`find tests -type f -name test.sh | wc -l` = 161（cli 17、convert 21、fsck 34、fuzz 9、misc 55、mkfs 25），与配方 `build()` 内 `os.walk` 统计一致。
- 执行位置：HarmonyOS PC 真机（HongMeng Kernel 1.12.0 / aarch64 / Toybox shell），源码为与 `conandata.yml` 同 SHA-256 的 v6.2 归档；用设备 `ohos-aarch64` profile 指向的 OHOS native SDK clang 15 + ld.lld 构建 btrfs-progs CLI，链接 harmonybrew 的 zlib/zstd/libuuid/libblkid。
- 执行方式：按上游 `<类别>-tests.sh` 驱动脚本的方式逐条跑 `bash ./test.sh`（`TOP`/`TEST_TOP`/`INTERNAL_BIN`/`RESULTS`/`IMAGE`/`TEST_DEV` 与驱动一致），单条 `timeout -s KILL 200`；退出码 0 且未打印 `[NOTRUN]`/`[SKIPPED]` 才记为通过。
- 结果：**通过 28 / 未运行 120 / 失败 13 = 161**。分类明细与逐条原因见 `test_package/MANIFEST.yml`。
- 未运行的主因（114 条）：上游 `tests/common` 的 `root_helper()` 要求 effective uid 为 0 才能挂载；真机登录用户是 uid 20001006 且平台无 sudo，脚本在执行任何命令前就打印 `[NOTRUN] Need to validate root privileges` 并以 0 退出——这类**不计为通过**。
- 为跑起测试工装而做、且只影响构建/运行环境的适配（不进入交付包）：config.guess 增加 HarmonyOS→`aarch64-unknown-linux-ohos` 识别；生成的 `config.status` 绕开 Toybox `mktemp -d` 在 HMDFS 上造出「owner 不可写目录」导致 `subs1.awk: Permission denied` 的分支；OHOS native libc 缺 `pthread_cancel`/`pthread_setcancelstate`/`pthread_setcanceltype`/`pthread_tryjoin_np`（仅 `btrfs scrub`、`btrfs rescue chunk-recover` 使用）故补链接期兼容归档；真机无 `/bin/bash`，用例改为显式 `bash ./test.sh`。
- 失败项的具体技术原因：`btrfs-convert` 未构建（目标机无 ext2fs/reiserfscore 开发库）5 条；`udevadm` 缺失（构建用 `--disable-libudev`）2 条；HMDFS 不支持 `fallocate(2)` 1 条；`mkfs.btrfs --rootdir` 填充所需的 POSIX ACL/chown 语义 2 条；其余 3 条为该文件系统上的扇区/节点大小组合与镜像截断路径、以及 Toybox `cp --sparse=auto` 不支持导致 `btrfs restore` 夹具解包失败。
- 结论口径：本包交付的是 libbtrfs 开发库，`library-test.c` 1/1 与消费者 2/2 是直接覆盖；仓库级 161 项套件已在同一真机、同一 v6.2 源码上逐条执行，其 28 条通过结果与 133 条未通过/未运行的逐条原因均如实记录，不以「环境不支持」一句带过。
