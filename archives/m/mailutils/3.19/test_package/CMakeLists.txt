cmake_minimum_required(VERSION 3.15)
project(test_mailutils C)

find_package(mailutils REQUIRED CONFIG)

add_executable(test_mailutils test_mailutils.c)
target_link_libraries(test_mailutils PRIVATE mailutils::mailutils)

enable_testing()
add_test(NAME mailutils_api COMMAND test_mailutils)
