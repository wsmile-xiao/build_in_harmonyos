# tinyxml2 10.1.0 HarmonyOS PC 移植说明

## 版本与源码

- 上游项目：<https://github.com/leethomason/tinyxml2>
- 官方标签：`10.1.0`
- 标签提交：`57eea48c5bfc354ac45d53b2eb499e66c80d63e0`
- 源码包 SHA-256：`9da7e1aebbf180ef6f39044b9740a4e96fa69e54a01318488512ae92ca97a685`
- 许可证：Zlib
- 外部依赖：无
- 上游源码补丁：无

10.1.0 包含构建修复、`size_t` 相关调整以及 CVE-2024-50615 修复。上游同时提示该版本存在小范围 API 返回类型变化，升级现有调用方时应重新编译并检查编译告警。

## Conan 适配

- 默认生成动态库，保留 `shared=False` 静态库选项。
- 使用上游 CMake 安装规则，导出 `tinyxml2::tinyxml2`、pkg-config 文件和 CMake config。
- 可运行目标产物的环境中自动执行上游 CTest；交叉构建仅编译上游测试，避免在 Windows 构建机误执行 OHOS ELF。
- HarmonyOS 原生 CTest 执行前签名构建树内的 `xmltest` 与 shared 库，并通过 `LD_LIBRARY_PATH` 暴露构建库目录。
- 为 CMake 未内置识别的 HarmonyOS 补齐 SONAME、RPATH 和 rpath-link linker contract，避免生成路径污染的动态依赖。
- OHOS 动态库打包时先移除旧代码签名段，再调用仓库规定的 `binary-sign-tool selfSign`。
- `test_package` 使用公开 CMake target，覆盖解析、类型化属性、实体、CDATA、序列化往返及错误路径，共 15 项断言。

## 验证结果

### Conan 主机回归

- WSL Linux x86_64，Conan 2.29.1：shared `conan create` 通过，上游 CTest 1/1 通过，消费者 15/15 通过。
- WSL Linux x86_64，Conan 2.29.1：static `conan create` 通过，上游 CTest 1/1 通过，消费者 15/15 通过。

### HarmonyOS 6.0 x86_64 模拟器

- 系统版本：`emulator 6.0.0.48(SP31DEVC00E47R1P3)`。
- SDK：OpenHarmony 26.0.0，Clang 15.0.4。
- static 上游 `xmltest`：`Pass 517, Fail 0`。
- static Conan 消费者：15/15 通过。
- shared 上游 `xmltest`：`Pass 517, Fail 0`。
- shared 消费者：15/15 通过。

### HarmonyOS arm64-v8a

- Windows 到 OHOS 的 Conan 交叉构建、打包和 `test_package` 编译/链接通过。
- `xmltest` 与消费者产物均经 ELF 头核对为 AArch64。
- 当前连接的模拟器为 x86_64，因此 arm64 产物未在该模拟器运行。

### 仓库检查与本地 CI

- `tests/run_all.py` 的仓库测试全部通过；其中 v12.20 在 Windows 上需把测试脚本固定的 OHOS Git 路径映射到本机 Git，映射后为 33/33 通过。
- 正式目标 CI 在正确的 `upstream/main` 增量基线下通过 G0、L0、KC、JC（10 个变更文件、1 个软件包）。
- CI 的 L1 使用原生 `ohos-aarch64` profile，当前 WSL/模拟器缺少 `/data/service/hnp/bin/binary-sign-tool`，因此在 Conan 配方校验阶段按设计中止；未伪造或跳过签名要求。

### PR #8776 CI 修复

- 首轮构建 #41816 已成功完成 CMake 配置、shared 库编译和 `xmltest` 链接，失败点位于 CTest 运行阶段；测试在约 0.01 秒内退出，未产生上游要求的 `Pass 517, Fail 0` 汇总。
- 首轮配方在 `build()` 中直接运行 CTest，而构建树 ELF 仅会在后续 `package()` 阶段签名；同时该 Worker 的 CMake 明确报告未知 HarmonyOS platform，构建树运行库路径没有可靠保障。
- 修复后遵循仓库 brotli/jsoncpp 的已验证模式：先签名构建树测试程序及 shared 库，设置构建目录 `LD_LIBRARY_PATH`，再使用 `ctest --output-on-failure --no-tests=error` 执行上游测试；安装后的 shared 库仍在 `package()` 中重新签名。

## 已知环境限制

当前本机 SDK 提供 `llvm-objcopy.exe`，但连接的模拟器不提供仓库约定路径下的 `binary-sign-tool`。因此本次已验证 shared 库在模拟器临时目录中的加载和运行，尚未在该环境复验配方的 shared 制品签名步骤。配方会在 OHOS shared 构建开始前检查签名工具并在缺失时明确失败，避免产出未签名包。

## 状态

`built`：源码校验、Conan shared/static 主机回归、OHOS x86_64 真机运行及 OHOS arm64 交叉编译均已完成；尚未发布。
