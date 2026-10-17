# yaze-ag 2.51.3 HarmonyOS PC 验证记录

- 看板：`yaze-ag/2.51.3` 由 `@tank_you` 认领，指定分支 `feat/yaze-ag-2.51.3`，活动「开源鸿蒙 PC 专项积分赛」10 火种。看板标为 C++，上游源码实际是 C。
- 上游：官方归档 `https://agl.yaze-ag.de/devel/yaze-ag-2.51.3.tar.gz`，SHA-256 `2b0a90c3bf3a27574b0427cf4579dc2347b371bec3fea5739e1527edf74b2809`；与 Homebrew 官方配方公布的哈希一致。Windows 与真机上传、独立回读的字节哈希一致。
- 真机：HarmonyOS PC AArch64，Conan 2.29.1；独立验证目录 `/data/storage/el2/base/haps/entry/files/yaze-ag-2.51.3-20260926T170600`。`conan graph info --build=never` 无 Conan 依赖。
- 原始故障：上游 `monitor.c` 使用 glibc 私有 `__S_IFMT`、`__S_IFREG`、`__S_IFDIR`，目标 musl 头文件不定义，原始编译报 6 个 undeclared identifier。仅将三处文件类型判断改为 POSIX `S_ISREG`/`S_ISDIR`，不改变磁盘读取逻辑。
- 正式配方：使用上游 ARMv8 Makefile，命令行指定 OHOS clang、`-O2` 和平台标识；不执行上游 `make install`，因为该目标含 `rm -rf $(LIBDIR)` 以及 `/tmp` 写入。将两个执行程序、引导文件、键盘映射、两张上游磁盘镜像与许可文本打入 Conan 包，另提供以包相对路径定位引导文件的 `yaze` 启动器。
- 最终验证：隔离 `CONAN_HOME`，`conan create recipe-v4 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 -c tools.build:jobs=1` 返回 0，日志 `create-v4.log` SHA-256 `2a2f4d10337e6f3b233cddb085fdb616b211110657004806a8ae293943e02691`。新增消费者测试从安装包启动模拟器，挂载并列出 A/B 两张磁盘，正常退出，打印 `YAZE-AG boot, disk mounts and monitor exit: PASS`。产物为 ELF64 AArch64，动态依赖仅 `libc.so`。
- 测试边界：上游归档中的 Makefile 提及 `test/`，实际归档无该目录，不能声称上游自动化测试已运行。新增消费者测试 1/1 通过；未运行完整 Z80 指令回归、CP/M 应用交互及全部镜像。编译有上游旧式函数声明等警告，未将其误报为零警告。
