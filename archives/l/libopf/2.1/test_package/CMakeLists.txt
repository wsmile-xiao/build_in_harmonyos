cmake_minimum_required(VERSION 3.15)
project(test_libopf C)

# Find the package via Conan-generated CMakeDeps
find_package(libopf REQUIRED)

add_executable(test_libopf test.c)
target_link_libraries(test_libopf libopf::libopf)

# HarmonyOS 平台专项测试（验证 aarch64 signed-char NIL 修复与聚类 label 越界修复）
add_executable(ohos_specific_test ohos_specific_test.c)
target_link_libraries(ohos_specific_test libopf::libopf)

enable_testing()
add_test(NAME test_libopf COMMAND test_libopf)
add_test(NAME ohos_specific_test COMMAND ohos_specific_test)