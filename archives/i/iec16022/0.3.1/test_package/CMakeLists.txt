cmake_minimum_required(VERSION 3.15)
project(test_iec16022 C)

# Resolve the installed iec16022 package through the CMakeDeps generator.
find_package(iec16022 REQUIRED)

add_executable(test_iec16022 test_iec16022.c)
target_link_libraries(test_iec16022 PRIVATE iec16022::iec16022)

enable_testing()
add_test(NAME test_iec16022 COMMAND test_iec16022)
