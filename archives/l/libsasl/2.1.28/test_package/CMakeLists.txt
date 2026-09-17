cmake_minimum_required(VERSION 3.16)
project(test_libsasl C)

find_package(libsasl REQUIRED CONFIG)

add_executable(test_libsasl test_libsasl.c)
target_link_libraries(test_libsasl PRIVATE libsasl::libsasl)

enable_testing()
add_test(NAME test_libsasl COMMAND test_libsasl)
