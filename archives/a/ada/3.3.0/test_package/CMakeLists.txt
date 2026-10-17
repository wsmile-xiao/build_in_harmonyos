cmake_minimum_required(VERSION 3.15)
project(test_ada C CXX)

# Find the package via Conan-generated CMakeDeps
find_package(ada REQUIRED)

add_executable(test_ada test.c)
target_link_libraries(test_ada ada::ada)

# Ensure C++ standard library is linked (ada is C++ internally)
if(NOT MSVC)
    target_link_options(test_ada PRIVATE -lc++ -lpthread)
endif()

enable_testing()
add_test(NAME test_ada COMMAND test_ada)
