cmake_minimum_required(VERSION 3.15)
project(test_caches CXX)

# Find the package via Conan-generated CMakeDeps
find_package(caches REQUIRED)

add_executable(test_caches test.cpp)
target_link_libraries(test_caches caches::caches)
set_target_properties(test_caches PROPERTIES CXX_STANDARD 17 CXX_STANDARD_REQUIRED ON)

# HarmonyOS 专项测试：验证 header-only 库在 OHOS (aarch64-linux-ohos) 平台真实可用
add_executable(test_caches_ohos ohos_specific_test.cpp)
target_link_libraries(test_caches_ohos caches::caches)
set_target_properties(test_caches_ohos PROPERTIES CXX_STANDARD 17 CXX_STANDARD_REQUIRED ON)

enable_testing()
add_test(NAME test_caches COMMAND test_caches)
add_test(NAME test_caches_ohos COMMAND test_caches_ohos)