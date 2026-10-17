cmake_minimum_required(VERSION 3.15)
project(test_primer3 C CXX)

# Find the package via Conan-generated CMakeDeps
find_package(primer3 REQUIRED)

add_executable(test_primer3 test.c)
# libprimer3.cc is C++11 (only C++ source upstream); link with the C++
# linker so libc++/stdc++ is pulled in automatically.
set_target_properties(test_primer3 PROPERTIES LINKER_LANGUAGE CXX)

target_link_libraries(test_primer3 primer3::primer3)

enable_testing()
add_test(NAME test_primer3 COMMAND test_primer3)
