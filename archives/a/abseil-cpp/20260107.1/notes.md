# abseil-cpp 20260107.1 适配笔记

## 构建方案

- 构建系统：CMake
- 目标平台：HarmonyOS PC AArch64
- 编译器：clang/clang++
- 版本：20260107.1
- 适配路径：路径 A（基础适配）

上游 Abseil 通过 CMake 安装头文件、静态库和 CMake 导出文件。配方关闭
`BUILD_TESTING`，避免将上游测试程序打入发布包；消费者测试通过 Conan
生成的 `abseil-cpp::abseil-cpp` 目标验证头文件、静态链接和运行时行为。

## 适配内容

1. 固定上游源码 URL 和 SHA-256，使用 Conan 2 `CMakeToolchain` 配置构建。
2. 强制 `ABSL_ENABLE_INSTALL=ON` 和位置无关代码，保证安装布局适用于下游。
3. 通过 `collect_libs()` 聚合 Abseil 组件静态库，并声明 HarmonyOS/Linux 的
   pthread 系统依赖。
4. 增加 Conan L1 消费者测试，验证 `absl::StrCat` 和 `absl::string_view`。

## 测试边界

上游 CTest 套件未在交叉构建阶段执行；适配后的消费者二进制需在 HarmonyOS PC
真机上运行。真机结果记录在同目录 `reports/test-report.md`。
