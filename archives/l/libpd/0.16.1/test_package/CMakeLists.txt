cmake_minimum_required(VERSION 3.15)
project(libpd_consumer_test LANGUAGES C)

set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)

find_package(libpd CONFIG REQUIRED)

add_executable(libpd_test libpd_test.c)
target_link_libraries(libpd_test PRIVATE libpd::libpd)

enable_testing()
add_test(NAME libpd_consumer_test
         COMMAND libpd_test libpdtest.pd ${CMAKE_CURRENT_BINARY_DIR})
