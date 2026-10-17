cmake_minimum_required(VERSION 3.15)
project(test_lib25519 C)

find_package(lib25519 REQUIRED)

add_executable(test_lib25519 test_lib25519.c randombytes_ohos.c)
target_link_libraries(test_lib25519 lib25519::lib25519)

enable_testing()
add_test(NAME test_lib25519 COMMAND test_lib25519)
