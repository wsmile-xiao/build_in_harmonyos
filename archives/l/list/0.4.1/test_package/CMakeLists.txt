cmake_minimum_required(VERSION 3.15)
project(test_list C)

# 通过 Conan 生成的 CMakeDeps 查找包
find_package(list REQUIRED)

add_executable(test_consumer test_consumer.c)
target_link_libraries(test_consumer list::list)

add_executable(test_ohos test_ohos.c)
target_link_libraries(test_ohos list::list)

enable_testing()
add_test(NAME test_consumer COMMAND test_consumer)
add_test(NAME test_ohos COMMAND test_ohos)