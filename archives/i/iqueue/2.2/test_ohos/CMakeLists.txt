cmake_minimum_required(VERSION 3.15)
project(test_ohos_iqueue LANGUAGES C)

find_package(iqueue REQUIRED)

add_executable(test_ohos_iqueue test_ohos.c)
target_link_libraries(test_ohos_iqueue PRIVATE iqueue::iqueue)
