cmake_minimum_required(VERSION 3.15)
project(test_ccmaker C)

find_package(ccmaker REQUIRED)

add_executable(test_add test_add.c)
target_link_libraries(test_add PRIVATE ccmaker::ccmaker)

add_executable(test_version test_version.c)
target_link_libraries(test_version PRIVATE ccmaker::ccmaker)

enable_testing()
add_test(NAME test_add COMMAND test_add)
add_test(NAME test_version COMMAND test_version)
