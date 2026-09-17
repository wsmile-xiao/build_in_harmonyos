cmake_minimum_required(VERSION 3.15)
project(test_libmpcdec C)

# Find the package through the Conan-generated CMakeDeps config
find_package(libmpcdec REQUIRED CONFIG)

add_executable(test_libmpcdec test_libmpcdec.c)
target_link_libraries(test_libmpcdec PRIVATE libmpcdec::libmpcdec)

if(UNIX)
    target_link_libraries(test_libmpcdec PRIVATE m)
endif()

enable_testing()
add_test(NAME test_libmpcdec COMMAND test_libmpcdec)
