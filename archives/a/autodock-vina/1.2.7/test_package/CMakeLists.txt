cmake_minimum_required(VERSION 3.15)
project(test_autodock_vina CXX)

enable_testing()

if(NOT VINA_EXECUTABLE)
    message(FATAL_ERROR "VINA_EXECUTABLE was not provided by Conan")
endif()

add_executable(vina_test_source test_source.cpp)
add_test(NAME vina_test_source COMMAND vina_test_source "${VINA_EXECUTABLE}")

add_test(NAME vina_version COMMAND "${VINA_EXECUTABLE}" --version)
set_tests_properties(vina_version PROPERTIES
    PASS_REGULAR_EXPRESSION "AutoDock Vina.*1\\.2\\.7")

add_test(NAME vina_help COMMAND "${VINA_EXECUTABLE}" --help)
set_tests_properties(vina_help PROPERTIES
    PASS_REGULAR_EXPRESSION "Input:")
