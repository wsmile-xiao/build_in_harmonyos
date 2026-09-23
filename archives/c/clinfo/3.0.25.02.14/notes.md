# clinfo 3.0.25.02.14 适配笔记

## 编译环境

- 构建系统：Makefile（纯 C）
- 编译日期：2026-09-08
- 目标平台：HarmonyOS PC aarch64
- 配方状态：built

## 上游与源码

- 上游仓库：https://github.com/Oblomov/clinfo
- 上游 tag：3.0.25.02.14
- 官方源码 SHA256：`48b77dc33315e6f760791a2984f98ea4bff28504ff37d460d8291585f49fcd3a`
- 许可证：CC0-1.0

## 适配方案

该版本沿用 3.0.23.01.25 已验证的最小 OHOS 方案：

1. 使用 KhronosGroup/OpenCL-Headers v2024.05.08 提供 `CL/cl.h`；
2. OHOS 分支从官方 OpenCL-ICD-Loader v2024.05.08 构建 `libOpenCL.so.1`；
3. `clinfo` 使用 `$ORIGIN` 在同目录加载打包的 ICD Loader；
4. 对 `clinfo` 和 `libOpenCL.so.1` 执行 HarmonyOS ELF 自签；
5. 覆盖上游 `-Werror -pedantic`，使用 clang 兼容的 C99 编译参数；
6. 不修改上游源码，不生成补丁。

## 依赖

- Conan 依赖：无
- Vendored 源码：OpenCL-Headers v2024.05.08、OpenCL-ICD-Loader v2024.05.08
- 运行时：包内 `bin/libOpenCL.so.1`

## 上游测试审计

官方 `3.0.25.02.14` tarball 共 22 个文件。源码树没有 `tests/`、`test/` 或测试源文件；
Makefile 仅提供 `all`、`clean`、`install`、`sparse`、`show`，没有 `check` 或 `test`
目标；`make -n check` 实际返回 `No rule to make target 'check'`。因此上游测试为
`0` 项，未删除或绕过任何测试。

## 消费者测试

`test_package/test_clinfo.sh` 包含 2 个真实断言：

1. `clinfo --version` 必须输出 `3.0.25.02.14`；
2. `clinfo` 必须实际加载 ICD Loader、完成平台/设备枚举，并输出 `Number of platforms`。

## 本机预验证

使用官方源码与 OpenCL-Headers v2024.05.08 在 macOS/Apple clang 17 上实际编译成功，
`clinfo --version` 正确输出 `3.0.25.02.14`。另外使用官方 OpenCL-ICD-Loader
v2024.05.08 构造无 vendor ICD 环境，消费者测试实际执行并达到 2/2 通过。

仓库 `conan-verify` 的 G1 配方完整性检查通过；G2 已实际完成三份官方源码下载，
随后因本机不存在 OHOS profile 指定的 `/data/service/hnp/bin/clang` 停止。该错误属于
本机缺少 HarmonyOS worker 工具链，不是源码或配方编译错误。

HarmonyOS W3 必须在具备 `/data/service/hnp` 工具链、ELF 签名工具和 OHOS Conan
profile 的真实 worker 上执行，不能由本机 macOS 构建替代。
