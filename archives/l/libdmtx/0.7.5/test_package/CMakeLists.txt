cmake_minimum_required(VERSION 3.15)
project(test_libdmtx C)

find_package(libdmtx REQUIRED)

add_executable(test_libdmtx test.c)
target_link_libraries(test_libdmtx libdmtx::libdmtx)

enable_testing()
add_test(NAME test_libdmtx COMMAND test_libdmtx)
