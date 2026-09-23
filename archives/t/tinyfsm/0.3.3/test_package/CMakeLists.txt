cmake_minimum_required(VERSION 3.15)
project(test_tinyfsm LANGUAGES CXX)

# Find the package via Conan-generated CMakeDeps
find_package(tinyfsm REQUIRED)

add_executable(test_tinyfsm test.cpp)
target_compile_features(test_tinyfsm PRIVATE cxx_std_11)
target_link_libraries(test_tinyfsm PRIVATE tinyfsm::tinyfsm)

enable_testing()
add_test(NAME test_tinyfsm COMMAND test_tinyfsm)