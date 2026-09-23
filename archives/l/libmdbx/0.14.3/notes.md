# libmdbx 0.14.3 适配笔记

## 基本信息

- 软件：libmdbx
- 版本：0.14.3
- 上游：<https://github.com/erthink/libmdbx>
- 许可证：Apache-2.0
- 归档：`v0.14.3.tar.gz`
- SHA-256：`a31118cfbe95ca73595b0ace5aba750e6dc40a3d34bb31ec89fb46b37b890816`

## 适配决策

- 使用上游 CMake 构建共享库，同时启用 C++ API。
- 关闭上游工具、man page 和库内测试，避免将不属于库包的可执行文件或测试带入包产物。
- Conan 包名保持任务权威名 `libmdbx`；上游实际库文件和 CMake 目标对应 `mdbx`，包目标导出为 `libmdbx::mdbx`。
- OHOS 的 CMake 系统名显式设为 `OHOS`，并固定安装库目录为 `lib`；这是为了匹配设备上的 CMake 平台模块和 Conan OHOS profile。
- 添加 `0001-ohos-skip-linux-kernel-version-gate.patch`：上游在 `mdbx_env_create()` 中无条件按 Linux `uname()` 版本拒绝低于 3.16 的内核；设备上的 HarmonyOS 兼容层报告 `1.12.0.0`，但实际提供目标 API，因此仅对 `__OHOS__` 跳过这项 Linux 版本门槛，其他 Linux 行为保持不变。
- 添加 `0002-ohos-preserve-working-lseek-offset.patch`：HarmonyOS 对约 4 TiB 的 `lseek` 返回 `EINVAL`，上游回退探测在找到约 2 TiB 的可用偏移后仍把失败候选写回共享停车偏移，导致后续锁文件 `lseek` 直接失败；补丁只保留最后一次成功候选。
- OHOS 构建显式关闭 `MDBX_USE_FALLOCATE`：设备 HMDFS 上 `posix_fallocate()` 返回 `EACCES`，但同一文件的 `pwrite()`/`ftruncate()` 可用；让 `osal_fsetsize()` 使用可用的截断扩展路径，避免新环境在 `mdbx_env_open()` 阶段失败。
- 仅声明 `pthread` 系统库；是否需要额外原子库由设备链接结果决定，不预先硬编码。

## 上游测试边界

`v0.14.3` 发布归档是精简的 amalgamated 源码包，不包含完整上游测试目录。归档内的 C++ 示例可作为上游 API 示例，但没有可直接纳入 Conan `build()` 的完整自动化测试套件，因此 `test_package` 补充 C API 和 C++ API 的真实消费者验证，并在设备上如实记录未覆盖项。

## 验证结果

- 设备侧原生 CMake configure、build 和 install 通过；OHOS 适配补丁均能应用。
- 最终设备 SHA `44eeab79570fb609414d8c1c27a6d044faa549ad` 上，C consumer 为 `21 passed, 0 failed`，C++ consumer 为 `8 passed, 0 failed`，OHOS 专项 consumer 为 `5 passed, 0 failed`。专项 consumer 仅在 `CMAKE_SYSTEM_NAME=OHOS` 或 `HarmonyOS` 时构建，验证 HMDFS 上的环境创建、打开、关闭和清理路径。
- W3 本地 CI 模拟通过：Conan create、test_package 执行、L4 补丁检查和 L5 库产物检查均通过；该包为纯库包，没有 `bin/`，L2 按规则跳过。
- 设备动态库加载检查确认产物为 AArch64 `DYN`，具备 GNU RELRO、不可执行栈和 `BIND_NOW`。
- 设备 HMDFS 上 `posix_fallocate()` 对新环境文件返回 `EACCES`，因此 OHOS 配方关闭 `MDBX_USE_FALLOCATE`，保留 `pwrite()`/`ftruncate()` 路径。

## 尚未闭环

- `conan-verify` 的 G4/L2/L4/L5 报告因 Conan 2.29 JSON 包 ID 解析兼容性问题跳过；实际包路径、文件清单、消费者、ELF 和 SHA-256 基线已在补充证据中单独记录。
- 人工 Review 的 `rule12_harmony_specific` 已通过新增 OHOS 专项 consumer 修复；W4、修复后的远端 CI 和 Review 闭环待完成。设备状态为 `built`，不代表已发布。
