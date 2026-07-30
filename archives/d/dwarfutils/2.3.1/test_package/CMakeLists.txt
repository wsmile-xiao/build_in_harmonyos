cmake_minimum_required(VERSION 3.16)
project(test_dwarfutils C)

find_package(dwarfutils REQUIRED)

add_executable(test_dwarfutils src/test_dwarfutils.c)
target_link_libraries(test_dwarfutils PRIVATE dwarfutils::dwarfutils)

enable_testing()
add_test(NAME dwarfutils_loaded COMMAND test_dwarfutils)
