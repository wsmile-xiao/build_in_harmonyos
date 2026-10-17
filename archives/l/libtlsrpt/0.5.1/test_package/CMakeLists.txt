cmake_minimum_required(VERSION 3.15)
project(test_libtlsrpt C)

find_package(libtlsrpt REQUIRED)

add_executable(test_libtlsrpt test.c)
target_link_libraries(test_libtlsrpt libtlsrpt::libtlsrpt)

enable_testing()
add_test(NAME test_libtlsrpt COMMAND test_libtlsrpt)
