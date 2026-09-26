cmake_minimum_required(VERSION 3.15)
project(test_cppcmd CXX)

# Find the package via Conan-generated CMakeDeps
find_package(cppcmd REQUIRED)

add_executable(test_cppcmd test.cpp)
target_link_libraries(test_cppcmd cppcmd::cppcmd)
target_compile_features(test_cppcmd PRIVATE cxx_std_17)

# HarmonyOS 专项测试（与上游 Catch2 测试、消费者测试分别计数）
add_executable(ohos_special_test ohos_special_test.cpp)
target_link_libraries(ohos_special_test cppcmd::cppcmd)
target_compile_features(ohos_special_test PRIVATE cxx_std_17)

enable_testing()
add_test(NAME test_cppcmd COMMAND test_cppcmd)
add_test(NAME ohos_special_test COMMAND ohos_special_test)