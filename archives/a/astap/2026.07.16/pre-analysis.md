# astap 2026.07.16 HarmonyOS PC 预分析

## 源码身份

- 上游镜像：`https://github.com/CanardConfit/ASTAP`
- 固定标签：`v2026.07.16`
- 标签提交：`efccff46c47886e80a71da8ad150880fcba14631`
- 源码 SHA-256：`e3349c722d097cceea201fe6dff39602853b5e344c1c8b863ed54eed9336e2e1`
- 语言：Object Pascal
- 构建系统：Lazarus/FPC（不是 Autotools）

## 推荐适配范围

优先适配无 GUI 的 `command-line_version/astap_command_line.lpr`，产出 `astap_cli`。GUI 版本依赖 Lazarus LCL、GTK/Qt 与 `libQt5Pas`，不适合作为首个 Conan 交付目标。

## 平台与工具链分析

| 检查项 | 结果 | 说明 |
|---|---|---|
| AArch64 | 已有上游工程 | `astap_command_line_linux_aarch64.lpi` 明确设置 `TargetCPU=aarch64` |
| OHOS 目标 | 需要验证 | 上游工程设置 `TargetOS=linux`；需要使用仓库已有 FPC 3.2.2 aarch64 工具链验证 HarmonyOS PC 运行兼容性 |
| GUI 依赖 | 首版排除 | CLI 不依赖 LCL widgetset，可避免 GTK/Qt5Pas 依赖链 |
| 线程 | 条件启用 | 主程序仅在 `UseCThreads` 定义时引入 `cthreads` |
| 压缩 | FPC 单元 | TIFF 代码使用 `zstream`，由 FPC packages 提供 |
| 星表数据库 | 运行时可选 | `-h` 和参数解析不需要星表；实际 plate solving 需要外部数据库 |
| 原始图像工具 | 运行时可选 | CLI 核心编译不要求打包 `dcraw`/`libraw` 辅助程序 |
| 上游测试 | 未发现 | 源码无独立自动化测试套件，需要 Conan `test_package` 覆盖 CLI 帮助、版本和错误路径 |

## 主要风险

1. 仓库登记的任务元数据误标为 Autotools，实际必须采用 custom FPC 构建。
2. FPC 3.2.2 现有包以 `aarch64-linux` RTL 为主，需要确认生成 ELF 在 OHOS musl 环境中的动态链接和系统调用兼容性。
3. ASTAP CLI 引用多个 FPC packages 单元；若现有 FPC 归档只有 RTL，需补齐 FCL、FreeVision、paszlib 等单元或使用可用预编译工具链。
4. 上游 `.lpi` 使用 Lazarus `lazbuild`，但可尝试直接用 `ppca64` 编译 `.lpr`，减少 Lazarus IDE 依赖。

## 实施方案

1. 使用固定标签源码和校验和创建 Conan custom-build 配方。
2. 依赖仓库已有 `fpc/3.2.2` 工具链，先直接编译 CLI；缺失单元时按错误日志补齐依赖。
3. 包内安装 `bin/astap_cli`、许可证及必要运行时数据说明，不打包大型星表。
4. 消费者测试至少覆盖 `astap_cli -h` 成功输出、无参数帮助、非法输入错误码和二进制架构/动态依赖检查。

## 结论

可适配，但属于 FPC/Lazarus 应用适配而非普通 C/C++ Autotools 库。首版应严格限定为命令行求解器，GUI 和星表数据库作为后续可选扩展。
