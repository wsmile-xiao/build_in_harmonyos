cmake_minimum_required(VERSION 3.15)
project(libaudit_consumer_tests LANGUAGES C)

find_package(libaudit REQUIRED)

add_executable(consumer_tests consumer_tests.c)
# consumer_tests calls both libaudit (tables/rules/netlink) and libauparse
# (event parsing) APIs — link both components explicitly.
target_link_libraries(consumer_tests PRIVATE
    libaudit::audit
    libaudit::auparse)

enable_testing()
add_test(NAME consumer_tests COMMAND consumer_tests)
