cmake_minimum_required(VERSION 3.10)
project(buddy_alloc_test_package C)

set(CMAKE_C_STANDARD 99)

find_package(buddy_alloc REQUIRED)

add_executable(test_consumer test_consumer.c)
target_link_libraries(test_consumer PRIVATE buddy_alloc::buddy_alloc)

add_executable(test_ohos test_ohos.c)
target_link_libraries(test_ohos PRIVATE buddy_alloc::buddy_alloc)

enable_testing()
add_test(NAME test_consumer COMMAND test_consumer)
add_test(NAME test_ohos COMMAND test_ohos)
