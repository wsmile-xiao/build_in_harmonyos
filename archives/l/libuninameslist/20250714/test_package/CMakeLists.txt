cmake_minimum_required(VERSION 3.15)
project(test_libuninameslist C)

# Find the package via Conan-generated CMakeDeps
find_package(libuninameslist REQUIRED)

# 消费者用例：仅通过公开头/公开 API/正常链接目标使用三方库
add_executable(test_libuninameslist test.c)
target_link_libraries(test_libuninameslist libuninameslist::libuninameslist)

# HarmonyOS 专项测试：数据完整性 + 公开 API 行为验证
add_executable(ohos_test ohos_test.c)
target_link_libraries(ohos_test libuninameslist::libuninameslist)

enable_testing()
add_test(NAME test_libuninameslist COMMAND test_libuninameslist)
add_test(NAME ohos_test COMMAND ohos_test)