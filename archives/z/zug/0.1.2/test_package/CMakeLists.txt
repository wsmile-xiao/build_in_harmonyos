cmake_minimum_required(VERSION 3.15)
project(test_zug CXX)

# 只 find_package 被测包；boost 由 zug 的 transitive_headers 带入
find_package(zug REQUIRED)

add_executable(test_zug test_zug.cpp)
target_link_libraries(test_zug PRIVATE zug::zug)
set_target_properties(test_zug PROPERTIES CXX_STANDARD 17 CXX_STANDARD_REQUIRED ON)

# 鸿蒙专项：类型擦除管道跨翻译单元实例化 + 管道状态隔离
add_executable(test_zug_ohos test_zug_ohos.cpp test_zug_ohos_tu2.cpp)
target_link_libraries(test_zug_ohos PRIVATE zug::zug)
set_target_properties(test_zug_ohos PROPERTIES CXX_STANDARD 17 CXX_STANDARD_REQUIRED ON)

enable_testing()
add_test(NAME test_zug COMMAND test_zug)
add_test(NAME test_zug_ohos COMMAND test_zug_ohos)
