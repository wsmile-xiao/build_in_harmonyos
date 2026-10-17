cmake_minimum_required(VERSION 3.15)
project(test_nob_consumer C)

find_package(nob.h CONFIG REQUIRED)

add_executable(test_nob_consumer test_nob_consumer.c)
target_link_libraries(test_nob_consumer PRIVATE nob.h::nob.h)
set_target_properties(test_nob_consumer PROPERTIES C_STANDARD 99 C_STANDARD_REQUIRED ON)

# 鸿蒙专项测试：OHOS 目标下 nob.h 的内存/字符串/UTF-8 边界行为验证
add_executable(test_nob_ohos test_nob_ohos.c)
target_link_libraries(test_nob_ohos PRIVATE nob.h::nob.h)
set_target_properties(test_nob_ohos PROPERTIES C_STANDARD 99 C_STANDARD_REQUIRED ON)

enable_testing()
add_test(NAME test_nob_consumer COMMAND test_nob_consumer)
add_test(NAME test_nob_ohos COMMAND test_nob_ohos)
