# gcem 1.18.0 适配笔记

## 基本信息

- 构建系统：CMake
- 类型：C++11 header-only `INTERFACE` library
- 上游：<https://github.com/kthohr/gcem/releases/tag/v1.18.0>
- 源码 URL：`https://github.com/kthohr/gcem/archive/refs/tags/v1.18.0.tar.gz`
- 源码 SHA256：`8e71a9f5b62956da6c409dda44b483f98c4a98ae72184f3aa4659ae5b3462e61`
- 第三方 Conan 依赖：无
- 源码修改/补丁：2 个最小补丁，见下文
- 当前状态：built（设备端完整复测完成后更新）

## 适配决策

上游 `CMakeLists.txt` 只安装 `include/` 头文件、CMake package config 和
`gcem` INTERFACE target，不生成库文件。配方使用 `package_type =
"header-library"`，`package_info()` 不声明链接库，并暴露 `gcem::gcem`。

上游 CMake 的最低版本为 3.1。HarmonyPC 当前 CMake 4 环境需要通过 Conan
toolchain 传入 `CMAKE_POLICY_VERSION_MINIMUM=3.5`；同时固定
`CMAKE_INSTALL_LIBDIR=lib`，使安装配置位于标准 `lib/cmake/gcem`。
这些是构建参数，不是上游源码补丁。

设备端发现 OHOS 的 `long double` 为 16 字节/113 位精度，但其
`std::log(1e-500L)`、`std::log(std::numeric_limits<long double>::min())`、
对应的 `log10`/`log2` 参照结果都为 `-inf`，尽管输入可表示且 `min()` 约为
`3.36e-4932`。上游 `log.cpp`、`log10.cpp`、`log2.cpp` 的六项依赖该 libc
参照函数，因此补丁 0002 仅在对应标准库参照值非有限时打印显式 skip 标记；补丁
0001 则把 `find_exponent.hpp` 的四个十进制阈值改为 long-double 字面量，
修复 128-bit `long double` 多减一个数量级的问题。另发现上游 sqrt 对此范围
的 Newton 初值在固定迭代次数内不收敛，补丁 0003 在小输入时先做比例缩放，
保持结果精度并避免增加递归深度。

## 构建与测试设计

上游 `tests/CMakeLists.txt` 通过 `file(GLOB ...)` 注册 46 个 `.cpp` 源文件，
每个生成一个 `<name>.test` 可执行文件，并聚合到 `gcem_tests` custom target；
它没有 `enable_testing()` 或 `add_test()`，所以不能只依赖 `cmake.test()`。
配方在 `cmake.build(target="gcem_tests")` 后枚举并运行 `tests/*.test` 的全部
46 个程序。`log.test`、`log10.test`、`log2.test` 仍然执行，但其中 6 个
OHOS libc 参照用例显式 skip；
其余上游可执行程序和可执行断言继续运行。`test_package` 另外从 Conan 安装包
编译/运行一个消费者程序，覆盖 7 个 constexpr 检查和 9 个运行时检查，包含
`log` 与 `incomplete_beta` 的 long-double 回归。

## 设备端验证

配方、补丁和测试内容的最终验证提交：`87aa6cb26852e9f04bb297422dfa15a7c53417af`；远端
`$HOME/ws/wt-gcem-1.18.0` HEAD 相同。设备工具链为 Conan 2.29.1、CMake
4.1.2、clang 15.0.4（target `aarch64-unknown-linux-ohos`）、OHOS
Kernel 1.12.0 aarch64。

执行命令（`tools.build:jobs=1`）：

```sh
conan create "$HOME/ws/wt-gcem-1.18.0/archives/g/gcem/1.18.0" \
  -pr:h="$HOME/ws/wt-gcem-1.18.0/ci/conan/profiles/ohos-aarch64" \
  -pr:b="$HOME/ws/wt-gcem-1.18.0/ci/conan/profiles/ohos-aarch64" \
  -c tools.build:jobs=1 --build=gcem/*
```

结果：该次 Conan create 返回 0，三个补丁应用成功，gcem header-only 包创建成功；
上游 46 个已注册可执行程序实际启动 46 个、返回通过 46 个、程序级失败 0
个；其中 `log.cpp`/`log10.cpp`/`log2.cpp` 的 6 个标准库 long-double 参照
case 按设备证据显式 skip，未伪报通过。`test_package` 消费者构建并原生运行
1/1，通过 16 项断言；未发生 runtime skip。

完整设备日志：`$HOME/tmp/gcem-1.18.0-87aa6cb-create.log`。

此前失败均保留在设备私有证据目录：第一次为 `incomplete_beta` 的真实
long-double 阈值错误；第二次和第五次为补丁 hunk 格式错误；第三、第四次为
新增证据驱动的 OHOS libc long-double 参照缺口。它们都没有被计入最终通过数。
