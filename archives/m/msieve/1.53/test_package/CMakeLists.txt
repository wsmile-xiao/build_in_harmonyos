cmake_minimum_required(VERSION 3.15)
project(msieve_test_package C)

# 消费者测试 + 鸿蒙特有测试，直接链接被测包 libmsieve.a 与其依赖
find_package(msieve REQUIRED)
find_package(gmp REQUIRED)
find_package(zlib REQUIRED)

add_executable(msieve_test test_package.c)
target_link_libraries(msieve_test PRIVATE msieve::msieve gmp::gmp zlib::zlib m)

add_executable(msieve_test_ohos test_ohos.c)
target_link_libraries(msieve_test_ohos PRIVATE msieve::msieve gmp::gmp zlib::zlib m)
