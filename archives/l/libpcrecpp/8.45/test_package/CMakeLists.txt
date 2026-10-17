cmake_minimum_required(VERSION 3.15)
project(test_pcrecpp CXX)

find_package(pcrecpp REQUIRED)
find_package(pcre REQUIRED)

add_executable(test_pcrecpp test.cpp)
target_link_libraries(test_pcrecpp PRIVATE pcrecpp::pcrecpp pcre::pcre)

# 鸿蒙特有测试：验证 __OHOS__ 宏 + OHOS 上 API 完整工作（rule12）
add_executable(test_ohos test_ohos.cpp)
target_link_libraries(test_ohos PRIVATE pcrecpp::pcrecpp pcre::pcre)

enable_testing()
add_test(NAME test_pcrecpp COMMAND test_pcrecpp)
add_test(NAME test_ohos COMMAND test_ohos)
