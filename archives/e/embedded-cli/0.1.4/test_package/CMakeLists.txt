cmake_minimum_required(VERSION 3.15)
project(test_embedded-cli C)

# Find the package via Conan-generated CMakeDeps
find_package(embedded-cli REQUIRED)

add_executable(test_embedded-cli test.c)
target_link_libraries(test_embedded-cli embedded-cli::embedded-cli)

enable_testing()
add_test(NAME test_embedded-cli COMMAND test_embedded-cli)

# HarmonyOS 专项测试：静态分配路径 + 公开 tokenize API + binding 回调
add_executable(ohos_static_alloc_test ohos_static_alloc_test.c)
target_link_libraries(ohos_static_alloc_test embedded-cli::embedded-cli)
add_test(NAME ohos_static_alloc_test COMMAND ohos_static_alloc_test)
