cmake_minimum_required(VERSION 3.15)
project(test_rang CXX)

find_package(rang REQUIRED)

add_executable(test_rang test.cpp)
target_link_libraries(test_rang PRIVATE rang::rang)
set_target_properties(test_rang PROPERTIES CXX_STANDARD 11)

# HarmonyOS 平台专项测试用例
add_executable(ohos_platform_test ohos_platform_test.cpp)
target_link_libraries(ohos_platform_test PRIVATE rang::rang)
set_target_properties(ohos_platform_test PROPERTIES CXX_STANDARD 11)

enable_testing()
add_test(NAME test_rang COMMAND test_rang)
add_test(NAME ohos_platform_test COMMAND ohos_platform_test)
