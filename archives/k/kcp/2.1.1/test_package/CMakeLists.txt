cmake_minimum_required(VERSION 3.15)
project(test_kcp LANGUAGES C)

find_package(kcp CONFIG REQUIRED)

add_executable(test_kcp test_kcp.c)
set_property(TARGET test_kcp PROPERTY C_STANDARD 99)
set_property(TARGET test_kcp PROPERTY C_STANDARD_REQUIRED ON)
target_link_libraries(test_kcp PRIVATE kcp::kcp)

enable_testing()
add_test(NAME test_kcp COMMAND test_kcp)
