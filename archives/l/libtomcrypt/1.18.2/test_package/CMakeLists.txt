cmake_minimum_required(VERSION 3.15)
project(test_libtomcrypt C)

find_package(libtomcrypt REQUIRED)
find_package(gmp REQUIRED)

add_executable(test_libtomcrypt test.c)
target_link_libraries(test_libtomcrypt libtomcrypt::libtomcrypt gmp::gmp)

enable_testing()
add_test(NAME test_libtomcrypt COMMAND test_libtomcrypt)
