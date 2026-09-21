cmake_minimum_required(VERSION 3.15)
project(test_libjwt2 C)

find_package(libjwt2 REQUIRED)
find_package(OpenSSL REQUIRED)

add_executable(test_libjwt2 test.c)
target_link_libraries(test_libjwt2 PRIVATE libjwt2::jwt)

enable_testing()
add_test(NAME test_libjwt2 COMMAND test_libjwt2)
