cmake_minimum_required(VERSION 3.15)
project(test_linalg.h CXX)

# Find the package via Conan-generated CMakeDeps
find_package(linalg.h REQUIRED)

add_executable(test_linalg.h test.cpp)
target_link_libraries(test_linalg.h linalg.h::linalg.h)
target_compile_features(test_linalg.h PRIVATE cxx_std_11)

# HarmonyOS 专项测试（真实可执行，验证 ABI 布局/constexpr/矩阵/四元数）
add_executable(test_ohos test_ohos.cpp)
target_link_libraries(test_ohos linalg.h::linalg.h)
target_compile_features(test_ohos PRIVATE cxx_std_11)

enable_testing()
add_test(NAME test_linalg.h COMMAND test_linalg.h)
add_test(NAME test_ohos COMMAND test_ohos)
