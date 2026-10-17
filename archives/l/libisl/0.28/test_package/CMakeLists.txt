cmake_minimum_required(VERSION 3.15)
project(test_libisl C)

find_package(libisl REQUIRED)

add_executable(test_libisl test.c)
target_link_libraries(test_libisl PRIVATE libisl::libisl)

enable_testing()
add_test(NAME test_libisl COMMAND test_libisl)
