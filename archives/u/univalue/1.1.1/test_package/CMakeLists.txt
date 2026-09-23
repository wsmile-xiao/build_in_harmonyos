cmake_minimum_required(VERSION 3.15)
project(test_univalue CXX)

# Find the package via Conan-generated CMakeDeps
find_package(univalue REQUIRED)

add_executable(test_univalue test.cpp)
target_link_libraries(test_univalue univalue::univalue)
target_compile_features(test_univalue PRIVATE cxx_std_11)

# HarmonyOS 专项测试（任务要求：真实可执行的 OHOS 平台验证用例）
add_executable(ohos_special_test ohos_special_test.cpp)
target_link_libraries(ohos_special_test univalue::univalue)
target_compile_features(ohos_special_test PRIVATE cxx_std_11)

enable_testing()
add_test(NAME test_univalue COMMAND test_univalue)
add_test(NAME ohos_special_test COMMAND ohos_special_test)