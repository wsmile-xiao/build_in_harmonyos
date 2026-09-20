cmake_minimum_required(VERSION 3.15)
project(test_uchardet C CXX)

# Find the package via Conan-generated CMakeDeps
find_package(uchardet REQUIRED)

add_executable(test_uchardet test.c)
target_link_libraries(test_uchardet uchardet::uchardet)

# uchardet is a C++ library exposing a C API: the test source stays C, but
# the final link must use the C++ driver so libc++ symbols (operator
# new/delete, __cxa typeinfo) referenced by libuchardet resolve.
set_target_properties(test_uchardet PROPERTIES LINKER_LANGUAGE CXX)

enable_testing()
add_test(NAME test_uchardet COMMAND test_uchardet)
