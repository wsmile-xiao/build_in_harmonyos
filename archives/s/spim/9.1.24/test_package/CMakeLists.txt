cmake_minimum_required(VERSION 3.15)
project(test_spim C)

# Find the package via Conan-generated CMakeDeps
find_package(spim REQUIRED)

add_executable(test_spim test.c)
target_link_libraries(test_spim PRIVATE spim::spim)

enable_testing()
add_test(NAME test_spim COMMAND test_spim
         WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR})
