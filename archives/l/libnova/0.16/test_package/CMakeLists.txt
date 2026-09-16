cmake_minimum_required(VERSION 3.15)
project(test_package C)

find_package(libnova REQUIRED)

add_executable(test_package test.c)
target_link_libraries(test_package PRIVATE libnova::libnova)

# OHOS-specific package check (test_ohos.sh C11): a second, independent
# consumer binary built from the same final package.
add_executable(ohos_check ohos_check.c)
target_link_libraries(ohos_check PRIVATE libnova::libnova)
