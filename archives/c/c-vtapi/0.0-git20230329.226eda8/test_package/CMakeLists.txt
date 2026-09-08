cmake_minimum_required(VERSION 3.15)
project(test_c-vtapi C)

# Find the package via Conan-generated CMakeDeps
find_package(c-vtapi REQUIRED)

add_executable(test_c-vtapi test.c)
target_link_libraries(test_c-vtapi c-vtapi::c-vtapi)
# See test_package/conanfile.py generate(): jansson's published CMakeDeps
# metadata omits include dirs; inject it for this consumer compile.
if(DEFINED JANSSON_INCLUDE_DIR)
  target_include_directories(test_c-vtapi PRIVATE ${JANSSON_INCLUDE_DIR})
endif()

# HarmonyOS 专项测试（离线、真实 API 调用）
add_executable(test_ohos test_ohos.c)
target_link_libraries(test_ohos c-vtapi::c-vtapi)
if(DEFINED JANSSON_INCLUDE_DIR)
  target_include_directories(test_ohos PRIVATE ${JANSSON_INCLUDE_DIR})
endif()

enable_testing()
add_test(NAME test_c-vtapi COMMAND test_c-vtapi)
add_test(NAME test_ohos COMMAND test_ohos)
