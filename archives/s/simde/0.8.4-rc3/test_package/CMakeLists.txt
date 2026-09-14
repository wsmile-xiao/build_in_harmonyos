cmake_minimum_required(VERSION 3.15)
project(test_simde C CXX)

# Find the package via Conan-generated CMakeDeps
find_package(simde REQUIRED)

# 消费者 1：C 模式的 simde 公开 API（NEON + SSE2 + wasm + MSA 便携路径 + 平台能力）
add_executable(test_simde test.c)
target_link_libraries(test_simde simde::simde)

# 消费者 2：C++ 模式（上游测试矩阵 c/cpp 双份注册对应的语言面）
add_executable(test_simde_cpp test_cpp.cpp)
target_link_libraries(test_simde_cpp simde::simde)

# 消费者 3：原生别名层（OHOS aarch64 原生 NEON 能力与别名一致性）
add_executable(test_native test_native.c)
target_link_libraries(test_native simde::simde)

enable_testing()
add_test(NAME test_simde COMMAND test_simde)
add_test(NAME test_simde_cpp COMMAND test_simde_cpp)
add_test(NAME test_native COMMAND test_native)
