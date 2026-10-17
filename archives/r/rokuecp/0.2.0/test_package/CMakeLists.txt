cmake_minimum_required(VERSION 3.15)
project(test_rokuecp C)

find_package(rokuecp CONFIG REQUIRED)

add_executable(test_rokuecp test_rokuecp.c)
target_link_libraries(test_rokuecp PRIVATE rokuecp::rokuecp)

add_executable(test_rokuecp_ohos test_rokuecp_ohos.c)
target_link_libraries(test_rokuecp_ohos PRIVATE rokuecp::rokuecp)

enable_testing()
add_test(NAME rokuecp_api COMMAND test_rokuecp)
add_test(NAME rokuecp_ohos COMMAND test_rokuecp_ohos)
