cmake_minimum_required(VERSION 3.15)
project(test_mtbl C)

find_package(mtbl CONFIG REQUIRED)
add_executable(test_mtbl test_mtbl.c)
target_link_libraries(test_mtbl mtbl::mtbl)
# the static snappy dependency inside libmtbl.a is C++ code: the pure-C test
# binary still needs the C++ runtime for its __cxa_* symbols (musl + libc++)
if(NOT MSVC)
    target_link_options(test_mtbl PRIVATE -lc++)
endif()
