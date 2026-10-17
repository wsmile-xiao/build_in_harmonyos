# itlib 1.12.2 — HarmonyOS PC 适配笔记

## 库概况

- **上游**：https://github.com/iboB/itlib（iboB's Template Libraries，MIT）
- **版本**：1.12.2（官方 tag v1.12.2）
- **类型**：header-only C++ 模板库集合，35 个头文件（`include/itlib/*.hpp`），
  覆盖 any/flat_map/flat_set/small_vector/static_vector/span/poly_span/expected/
  generator/ufunction/pmr_allocator/pod_vector/strutil/qalgorithm 等
- **构建系统**：CMake（INTERFACE 目标 `itlib::itlib`，FILE_SET HEADERS 安装，
  install(EXPORT itlib-targets) 导出 CMake package config）
- **依赖**：无（仅 C++ 标准库，C++11 起；无运行时、无编译期第三方依赖）

## 适配要点

1. **header-only 无编译**：`package_type = "header-library"`，settings 四项齐全，
   `no` 编译产物，package() 由 `cmake.install()` 完成（上游已在 install 规则
   中安装头文件与 CMake target export）。
2. **OHOS 平台语义**：`CMAKE_SYSTEM_NAME` 设为 Linux（R32：recipe 内 os 判断
   用 `in ("Linux","OHOS")`；本项目惯例纯头文件库保持 Linux 语义，无平台特化
   代码路径）。
3. **上游测试与 CI 隔离（E342 口径）**：上游测试通过 CPM（get_cpm.cmake）在
   configure 期从 GitHub 拉取 doctest/icm/doctest-util/picobench，离线/受限
   CI 下不可控，且当前直连 GitHub 不可达。因此 conan create 关闭
   `ITLIB_BUILD_TESTS=OFF`，上游测试在本地单独构建运行（见
   reports/upstream-test-ledger.md，双口径台账），消费者验证由 test_package
   承担（R34 实质调用公开 API）。
4. **无补丁**：纯头文件、仅标准库依赖，OHOS libc 兼容，无源码修改。

## 测试统计（双口径）

- 源码声明总数：见 reports/upstream-test-ledger.md（按 t-*.cpp 逐一枚举
  TEST_CASE，含 .inl 共享用例）
- 当前配置可执行集合：本地 ITLIB_BUILD_TESTS=ON 独立构建运行（CPM 依赖
  经镜像缓存）
- 鸿蒙专项：test_package 消费者用例（test_itlib.cpp）实质调用公开头文件 API

## 结果

- conan create：见 reports/conan-create.log / .ci-result.json
- 消费者验证：test_package PASS