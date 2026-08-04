# abseil-cpp 20260107.1 验证报告

## 验证环境

- 设备：HarmonyOS PC 真机 2
- 地址：`10.62.135.191:2222`
- 架构：AArch64
- 编译器：`aarch64-unknown-linux-ohos-clang` 15.0.4
- 构建工具：CMake 4.1.2、Ninja 1.13.1
- 构建选项：`CMAKE_CXX_STANDARD=17`、`ABSL_ENABLE_INSTALL=ON`、
  `BUILD_TESTING=OFF`、`CMAKE_POSITION_INDEPENDENT_CODE=ON`

## 构建与安装

- 上游源码配置：通过 CMake 成功完成。
- 构建结果：247 个 Ninja 目标全部完成。
- 安装结果：安装目录包含 303 个文件，生成
  `lib/cmake/absl/abslConfig.cmake`。
- 设备侧 ELF：消费者程序为 64-bit arm64，动态依赖为
  `libc++_shared.so` 和 `libc.so`。

## 消费者测试

测试使用 `absl::strings` 导出目标，编译并运行以下断言：

1. `absl::StrCat("abseil-cpp ", "20260107.1")` 返回预期字符串。
2. `absl::string_view` 与预期字符串比较成功。
3. 进程正常退出并打印 `abseil-cpp 20260107.1`。

结果：1/1 通过，退出码 `0`。

消费者二进制 SHA-256：
`95ca03d26fb5a03afa6f9f269243f70b319800b12e0fd2e941a63017a23cf74f`

## 测试边界

本次 Conan 包构建关闭上游 CTest，仅执行消费者视角的真机验证；未将未执行的
上游测试套件计入通过率。
