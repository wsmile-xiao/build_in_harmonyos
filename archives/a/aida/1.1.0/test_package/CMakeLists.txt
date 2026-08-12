cmake_minimum_required(VERSION 3.15)
project(test_aida C)

# Find the package via Conan-generated CMakeDeps
find_package(aida REQUIRED)

add_executable(test_aida test.c)
target_link_libraries(test_aida aida::aida ${CMAKE_DL_LIBS})

enable_testing()
add_test(NAME test_aida COMMAND test_aida)
