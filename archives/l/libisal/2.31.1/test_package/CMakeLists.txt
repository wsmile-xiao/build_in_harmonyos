cmake_minimum_required(VERSION 3.15)
project(test_libisal C)

find_package(libisal REQUIRED)

add_executable(test_libisal test.c)
target_link_libraries(test_libisal PRIVATE libisal::isal)

enable_testing()
add_test(NAME test_libisal COMMAND test_libisal)
