# re2 2025-11-05 适配笔记

## 版本选择
- 上游 google/re2 官方 release tarball，2025 年最新稳定 tag：**2025-11-05**。
  2025 年 tag 序列：2025-07-17 / 07-22 / 08-05 / 08-12 / 11-05（tags API 实测）。
- conandata.yml URL：https://github.com/google/re2/archive/2025-11-05.tar.gz（官方源，R39）
  sha256: 87f6029d2f6de8aa023654240a03ada90e876ce9a4676e258dd01ea4c26ffd67（实测下载计算）

## 依赖（W0）
- abseil-cpp/20260107.1 已发布于 ohpcd 制品仓（conan list 实测存在；另有 20240116.1）。
  沿用 2024-04-01 配方同一依赖，无新增依赖。

## 与 2024-04-01 配方的差异
- 上游 CMakeLists.txt cmake_minimum_required 升至 3.22（CI CMake 满足）。
- absl 依赖结构不变：仍 find_package(absl REQUIRED) + absl::* 目标 → 继续使用
  absl_DIR 指向 abseil-cpp 包内 lib/cmake/absl/ 的真实 abslConfig.cmake（同 protobuf/33.6 模式）。
- 无需补丁，patches: {}。

## 上游测试清点（R51）
- 上游测试：re2/testing/*.cc（re2_test.cc 等由 RE2_BUILD_TESTING=ON + ctest 驱动），
  Makefile runtests 脚本。conan 配方 RE2_BUILD_TESTING=OFF（与 2024-04-01 一致），
  由 test_package consumer 测试实质覆盖 API（FullMatch/PartialMatch/Replace/GlobalReplace）。
- 上游测试在 CI 交叉编译环境无法在宿主机运行（OHOS aarch64 二进制）；
  test_package 在 OHOS 下以"交叉编译+链接成功"为验证点，非 OHOS 平台执行运行时断言。

## 遗留目录处理
- archives/r/re2/2024-04-01（已发布 published）：**未改动**。
- archives/r/re2/2024-07-01（partial 残留，仅 manifest/_meta/README）：保留未动，
  不影响本配方（L0n 要求变更限于本版本目录）。

## commands.json
- re2 构建产物只有 lib/libre2.a|so（纯库，package_info 仅 cpp_info.libs），不产出
  可执行文件 → 按 R38/L0k 库类型不需要 commands.json，软件级目录无该文件属正常。
