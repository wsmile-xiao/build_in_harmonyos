cmake_minimum_required(VERSION 3.15)
project(test_ctrl_c LANGUAGES CXX)

# Find the package via Conan-generated CMakeDeps
find_package(ctrl-c CONFIG REQUIRED)

add_executable(test_ctrl_c test_ctrl_c.cpp)
target_link_libraries(test_ctrl_c PRIVATE ctrl-c::ctrl-c)
target_compile_features(test_ctrl_c PRIVATE cxx_std_11)
set_target_properties(test_ctrl_c PROPERTIES
    RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/bin")

enable_testing()
add_test(NAME test_ctrl_c COMMAND test_ctrl_c)
