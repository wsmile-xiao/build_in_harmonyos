# libsbig 4.9.9 适配笔记

## 编译环境

- 构建系统: custom（无编译步骤——上游为预编译二进制分发，配方只挑 blob + 补齐 soname 符号链打包）
- 编译日期: 2026-09-30
- 编译器: 不适用（build() 为空；消费者/CI 工具链为 clang 15 / aarch64-linux-ohos）
- 状态: built
- 平台任务: 鸿蒙 PC（HarmonyOS PC arm64）三方库适配；本子任务负责 4.9.9 剩余文件（test_package/ + notes.md + manifest.yaml），conanfile.py/conandata.yml 由前序子任务完成（勿改动）
- 上游: indilib/indi-3rdparty 的 libsbig 目录（Debian non-free pool 的 orig 源码包）
- 源码 sha256: `02df9d7e47d5bfea0adb9b4126251f7ab0587097bdbea9e0f5d749a14779cf4a`

## 上游测试清点（R51，附清点证据）

**结论：libsbig 4.9.9 上游确无任何测试。** 上游是预编译二进制分发，无 C 源码、无 tests/、无 ctest 注册、无可执行测试程序。

清点过程（2026-09-30 对 `libsbig_4.9.9.orig.tar.gz` 解压后逐项核对）：

1. **顶层文件清单**：`libsbig_arm64.bin` / `libsbig_x64.bin` / `libsbig_armhf.bin` / `SBIGUDrvOSX.bin`（预编译共享库 blob）+ `sbigudrv.h`（唯一头文件）+ `sbigucam.hex`/`sbiglcam.hex`/`sbigfcam.hex`/`sbigpcam.hex`/`stfga.bin`（固件）+ `CMakeLists.txt` + `libsbig.spec` + `51-sbig-debian.rules` + `LICENSE.firmware` + `cmake_modules/` + `indi-3rdparty-infos/`。**没有 C 源码文件**（无 .c/.cpp）。
2. **tests/ 目录**：`find . -type d` 仅 `.`、`./cmake_modules`、`./indi-3rdparty-infos`——**无 tests/ 目录**。
3. **测试文件**：`find . -iname '*test*'` **无输出**——无任何 *test* 命名的文件。
4. **ctest 注册**：`CMakeLists.txt` 无 `enable_testing()` / `add_test` / `check` / `test` 字样——**无 ctest 注册**。
5. **spec 测试段**：`libsbig.spec` 无 `%check` / `test` 段。
6. 上游 CMakeLists.txt 仅做 `add_library(sbig SHARED IMPORTED)` + 挑 blob + install 头文件/固件/udev 规则——纯安装逻辑，无测试目标。

→ 上游 N=0，无任何测试可运行，MANIFEST.yml 中 `upstream_tests: []`、`upstream_test_in_build: false`（R51 如实申报）。

## 编译步骤

1. `source()` 拉取 Debian orig 源码包并按 sha256 校验（conandata.yml）。
2. `build()` 为空（R33 不适用：不裸用 `${CC}`/`${CFLAGS}`；无源码可编译）。
3. `package()` 按 `settings.arch` 挑选 blob（armv8 → `libsbig_arm64.bin`，x86_64 → `libsbig_x64.bin`，其余 arch 抛 `ConanInvalidConfiguration`），复制为 `lib/libsbig.so.4.9.9` 并补齐 soname 符号链（`libsbig.so.4`、`libsbig.so`）。
4. 头文件装 `include/libsbig/sbigudrv.h`；固件装 `res/sbig`（不写系统 `/lib/firmware`）；LICENSE.firmware / 51-sbig-debian.rules / libsbig.spec 文档化入包。
5. 包内对 .so 做 ELF 自签名（`binary-sign-tool` 存在才签，方法内 guard；OHOS 拒绝加载未签名 .so，E318 同类，沿用 systemd 261.1 做法）。
6. `package_info()`：`cpp_info.libs=["sbig"]`，`includedirs=["include/libsbig"]`，CMake 目标 `libsbig::libsbig`，Linux/OHOS 追加系统库 `m`。
7. 消费者验证走 test_package：`find_package(libsbig REQUIRED CONFIG)` + `target_link_libraries(libsbig::libsbig)`，test.c 链接并调用真实 `SBIGUnivDrvCommand()`（见下）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游无 C 源码可编译 | 预编译二进制分发（.bin/.h/.hex/.spec） | 配方不做编译（build() 空），按 arch 挑 blob 打包；R51 上游测试 N=0 如实申报 |
| 2 | 预编译 .so 在 OHOS 设备 dlopen/链接加载被拒（Permission denied） | OHOS 要求 ELF 自签名（E318） | package() 末尾用 binary-sign-tool 自签名，工具缺失则跳过（guard，不依赖 settings.os） |
| 3 | 无硬件运行时 test 的驱动调用返回错误码 | SBIG 相机/USB 设备不存在 | test.c 将返回码如实记录为"非崩溃成功"；仅 CE_UNKNOWN_COMMAND / 越界码 / GetDriverInfo 结果未回填才判失败 |

## 源码修改

无补丁（R1：无源码可改；patches/ 空）。

## 依赖版本

- eudev/3.2.14（libsbig_arm64.bin 的 DT_NEEDED 含 `libudev.so.1`，由 eudev recipe 依赖提供；已发布 ohpcd 制品仓，见 W0）

## W0 依赖发布检查结论

- 依赖清单：`eudev/3.2.14`（唯一）。
- 检查方式（R35：禁止 conan list，用 `conan download --only-recipe`）：`conan download eudev/3.2.14 -r=ohpcd --only-recipe` → 通过。
- 佐证：eudev/3.2.14 在 `archives/e/eudev/3.2.14/` 已归档，且 `ledmon`、`libcec-tools`、`libdvbv5`、`libinput`、`libtype` 等多个已合入/发布的下游包均 `requires("eudev/3.2.14")`（R36 依赖先发布再构建下游，能发布 = 依赖已上线）。
- 结论：**依赖已发布，可正常继续适配，无阻塞。**

## 验证结果

```bash
# 配方自包含构建（W3，由 finish step [5/10] 执行，本子任务不做）：
#   conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
# 消费者测试（test_package，CTest target=libsbig_consumer，测试目标 test_libsbig）：
#   cmake.test() 执行 add_test(NAME libsbig_consumer COMMAND test_libsbig)
# 无相机时预期输出（示例）：
#   CC_OPEN_DRIVER returned 2            (CE_DRIVER_NOT_FOUND，记录返回码非崩溃)
#   ok:   CC_OPEN_DRIVER
