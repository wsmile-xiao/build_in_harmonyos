cmake_minimum_required(VERSION 3.16)
project(test_cotp C)

find_package(COTP REQUIRED)

add_executable(test_cotp test_cotp.c)
target_link_libraries(test_cotp PRIVATE COTP::cotp)

enable_testing()
add_test(NAME test_cotp COMMAND test_cotp)

if(DEFINED LIBCOTP_TEST_RPATH AND NOT LIBCOTP_TEST_RPATH STREQUAL "")
    target_link_options(test_cotp PRIVATE "-Wl,-rpath,${LIBCOTP_TEST_RPATH}")
endif()
