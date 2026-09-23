# lzham 1.0 适配笔记

## 当前状态

macOS 侧已完成配方、CMake/OHOS 可移植性补丁、完整 `test_package` 和 manifest 的独立核对。候选分支已推送至 AtomGit fork；设备侧按新工作流在独立私有目录中完成 W0、原生构建、Conan/W3 和消费者补充验证。最终版本状态为 `built`；`published`、PR、CI 和 Review 属后续 GitCode 闭环，不在本文件中提前宣称。

## 来源核对

- 上游仓库：[richgel999/lzham_codec](https://github.com/richgel999/lzham_codec)
- 版本：`v1_0_release`（GitHub tag，提交 `6ce4d59`）
- 许可证：MIT（以 release tarball 内 `LICENSE` 为准）
- 源码归档 SHA-256：`41568ecb0746b769b49704594bdcea98d1e3d605cabd2fc225e72edb508837c3`
- 直接 Conan 依赖：无

## 源码与补丁判断

上游根 CMake 仅递归进入四个旧式子目录；其中 `lzhamdecomp`、`lzhamcomp` 和 `lzhamdll` 的链接声明分别存在错误或自链接，且没有 install 规则。`0001-cmake-install-and-ansi-path.patch` 将压缩、解压和 `lzhamlib` 的公开 C API 组成单一 `lzham` 目标，安装 public headers，并把上游 `lzhamtest` 的无参数内存测试注册为 CTest。配方通过 `LZHAM_ANSI_CPLUSPLUS=1` 使用上游明确提供的无线程路径，避免 OHOS aarch64 落入未声明的 pthread/原子实现。

OHOS 侧的 `stdint.h` limit 宏冲突由 `0002` 独立处理；对齐分配 helper、malloc 和 realloc 分拆为 `0003`、`0004`、`0005`，以适配设备 Toybox `patch` 对单文件单 hunk 的实际行为。平台条件采用设备 clang 同时提供的 POSIX/Linux 判断，避免在补丁新增 `__OHOS__` 宏；后三个补丁同时修复上游测试暴露的 16 字节分配对齐要求。

## 已执行的 macOS 检查

- 官方 release tarball 已下载并核对 SHA-256；目录、CMake、public headers、license 和测试入口已完成静态核对。
- `conandata.yml` 的五个 `patch_file`、`patches/` 中的五个实际文件和版本 manifest 的 `patches_applied` 已逐项一致。
- 已用项目本地 Python 入口完成配方/test_package 静态检查；未在 macOS 运行 CMake configure/build/install、Conan、ELF 检查或任何鸿蒙运行测试。

## 设备验证结果

### W0 与原生构建

- 设备 `$HOME` 核对为 `/storage/Users/currentUser`；任务 worktree 使用 AtomGit fork，分支为 `feat/lzham-1.0`，稀疏范围包含目标归档、脚本、模板、知识和测试目录。
- 设备 Python 为 3.12.8，Conan 为 2.29.1，clang/clang++ 为 15.0.4，目标为 `aarch64-unknown-linux-ohos`；语言预检识别为 C++ 主体。
- release tarball SHA-256 与声明一致；源码依赖扫描未发现外部 Conan 或 pkg-config 依赖。
- 五个补丁按 `0001` 至 `0005` 顺序成功应用。原生 CMake configure、单并发构建和 install 均通过。
- `ctest --output-on-failure`：`1/1` 通过，`0` 失败；测试名为 `lzham_upstream_smoke`。

### Conan/W3 与消费者验证

- 真清理目标 Conan reference 的 source/build/download/temp/backup 及 `p/` 分片后，干净 `conan create` 成功；配方使用 OHOS `armv8`、clang 15、C++17、libc++ profile。
- `test_package` 真实完成 CMake 构建并运行，消费者链接目标为 `lzham::lzham`，运行输出为 `LZHAM round-trip OK: 65536 -> 1613 bytes`。
- 由于设备旧 verifier 对 Conan 2.29 的完整 reference/revision/package JSON 层级曾出现“找不到 package ID 仍报 PASS”的假绿，未把该旧报告的 G4/L2/L4/L5 跳过项当作通过。已补做并留存：六项静态库/头文件产物清单及 SHA-256（G4）、消费者实际运行（L2）、AArch64 PIE/NX/full RELRO 检查（L4）和六项产物基线（L5）。
- 所有设备命令、工作目录、开始/结束时间、stdout、stderr、退出码和原始报告均留在任务私有证据目录；干净 `conan-create` 日志在 `finish` 内部缓存重跑覆盖前已单独保存。

## finish 收尾

`finish lzham 1.0 built` 已在设备任务 worktree 执行。归档状态被写为 `built`，但外层命令实际非零退出，未将其改报 PASS。非零项与统一工作流登记的工具/存量检查边界一致：CMake/Conan 工程被硬编码 `./configure` 的 G0 预检、legacy submit-only 文件预检、存量知识条目和 W2/SUMMARY 陈旧基线；有效 Conan/W3 证据仍以清缓存轮和上述人工补充为准。

`finish` 产生的 `SUMMARY.md` 重建、镜像版 `conandata.yml`、版本 manifest/notes 自动写入、缓存 tarball、备份文件和忽略构建目录均已在设备逐项审查后恢复或精确清理，未进入候选提交。设备主检出保持原有用户修改不变。

## 最终状态

代码、配方和设备证据已完成到 `built` 阶段。GitCode PR、CI 和 AI Review 必须在最终 SHA 定稿、双端 SHA/状态一致且 W4 独立审计通过后继续；相关数字和结论以 macOS 本地 API/CI/Review 原始回读为准。

## Review 补充

2026-09-10 人工评审指出 `rule12_harmony_specific` 计数为 0，并要求复核 `test_package`。原有 `test_lzham.c` 是普通消费者测试，确实没有被归入鸿蒙专项测试。后续新增 `test_ohos.c`，由 Conan 的 `settings.os=OHOS` 显式启用；它在编译期确认 `__OHOS__`/`__linux__` 平台宏，运行期以 10 个跨越 16 字节边界的输入长度执行公开压缩/解压 API，覆盖本适配的对齐分配与重分配路径。该测试单列为 1 个鸿蒙特有消费者测试，不混入上游 CTest 数。
