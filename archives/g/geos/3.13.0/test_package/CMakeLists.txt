cmake_minimum_required(VERSION 3.15)
project(geos_test CXX C)

find_package(GEOS CONFIG REQUIRED)

add_executable(geos_test test.c)
target_link_libraries(geos_test GEOS::geos_c)
# geos_c 是 C++ 库，需要链接 C++ 标准库 (libc++)
set_target_properties(geos_test PROPERTIES LINKER_LANGUAGE CXX)

enable_testing()
add_test(NAME geos_test COMMAND geos_test)
