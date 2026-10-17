cmake_minimum_required(VERSION 3.15)
project(test_libdisorder C)

find_package(libdisorder CONFIG REQUIRED)

add_executable(test_api test_api.c)
target_link_libraries(test_api PRIVATE libdisorder::libdisorder)

add_executable(test_ohos test_ohos.c)
target_link_libraries(test_ohos PRIVATE libdisorder::libdisorder)

enable_testing()
add_test(NAME libdisorder_api COMMAND test_api)
add_test(NAME libdisorder_ohos_entropy COMMAND test_ohos)

