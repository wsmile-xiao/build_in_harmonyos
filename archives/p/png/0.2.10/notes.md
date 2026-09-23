# png++ 0.2.10 HarmonyOS PC 移植说明

## 包身份与源码

- 本仓库归档和 Conan 引用：`png/0.2.10`。
- 对应 Conan Center 配方：`pngpp/0.2.10`。
- 上游项目：png++，libpng 的 header-only C++ 封装。
- 官方源码：`png++-0.2.10.tar.gz`。
- SHA-256：`998af216ab16ebb88543fbaa2dbb9175855e944775b66f2996fc945c8444eee1`。
- 许可证：BSD-3-Clause。
- 依赖：`libpng/1.6.58.2`，并由其传递使用 zlib。

归档名采用 `png`，是为了满足仓库分支名、目录名和 `conanfile.py` 中 `name` 一致的检查；源码和公开 C++ 命名空间仍保持上游的 `png++` / `png`。

## 适配内容

png++ 0.2.10 的 `config.hpp` 只识别 glibc、Windows、Apple、FreeBSD 和 Solaris 的字节序接口。HarmonyOS 使用 musl，OHOS Clang 15 已提供 `__BYTE_ORDER__`、`__ORDER_LITTLE_ENDIAN__` 和 `__ORDER_BIG_ENDIAN__`，因此补丁直接采用这些编译器宏，不硬编码系统名或架构。

Conan 配方按 header-only 包处理：

- `package_type = "header-library"`、`no_copy_source = True`；
- 包 ID 清空，不为不同架构重复生成相同头文件包；
- 安装 29 个 `*.hpp` 到 `include/png++`，并安装 `COPYING`；
- 导出 CMake 目标 `png::png`；
- 精确依赖 `libpng/1.6.58.2`，消费者可获得传递 include/link 信息。

## 验证结果

### Conan 与消费者测试

- TDD RED：仅存在 `test_package` 时，`conan create` 按预期因缺少 `conanfile.py` 失败。
- Windows 到 OHOS arm64 交叉构建：Conan 2.29.1、OpenHarmony SDK 26.0.0、Clang 15.0.4；配方导出、源码校验、补丁、29 个头文件打包、消费程序编译和链接全部通过，ELF 为 AArch64。
- HarmonyOS 6.0 x86_64 虚拟机：消费程序创建 3x2 RGB PNG 后重新读取，文件存在、尺寸和 6 个像素共 9/9 项断言通过。

### 上游测试清点与执行

上游测试入口为 `make test`，会编译 7 个测试程序，并对 97 个 PngSuite 文件及生成文件执行 1,566 次字节级比较。另有 `make test-compile-headers` 的 29 个头文件独立编译检查，以及 `make examples` 的 1 个官方示例。

- OHOS x86_64：7/7 测试程序编译通过；`make test` 等价执行结果为 1,492/1,566 字节级比较通过。
- 74 个失败是 PB/PB2 重复产生的 37 个唯一旧金样本差异：其中 5 个 PNG 解码后尺寸和像素完全一致，仅编码字节不同；其余 32 个均为 RGB→灰度，最大通道偏差严格为 1 个输出 LSB。
- 同一 74/1,566 结果在 WSL x86_64 + libpng 1.6.43 复现；改用 png++ 发布同期的 libpng 1.6.37 也完全一致。因此该差异不是 HarmonyOS 特有回归，不修改或重生成上游金样本以掩盖事实。
- 29/29 公共头文件通过 OHOS x86_64 独立编译。
- 官方 `pixel_generator` 示例在虚拟机运行成功，生成有效的 32x512、1-bit 灰度 PNG。

### 设备信息

- 连接目标：`127.0.0.1:5555`。
- 内核架构：x86_64。
- HDC：3.2.0f。
- 系统：HarmonyOS 6.0 PC 虚拟机。

## 状态

`built`：源码与哈希已核验，arm64 Conan 交叉构建/打包/消费端链接通过，x86_64 HarmonyOS 真机消费测试与官方示例通过；上游旧金样本差异已完整量化并以跨平台对照确认。
---

**编译结束**: 2026-09-07 21:43
**最终状态**: built
