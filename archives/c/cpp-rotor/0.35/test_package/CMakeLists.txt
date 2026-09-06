cmake_minimum_required(VERSION 3.15)
project(test_cpp-rotor CXX)

# Find the package via Conan-generated CMakeDeps
find_package(cpp-rotor REQUIRED)

add_executable(test_cpp-rotor test.cpp)
target_compile_features(test_cpp-rotor PRIVATE cxx_std_17)
target_link_libraries(test_cpp-rotor cpp-rotor::cpp-rotor)

enable_testing()
add_test(NAME test_cpp-rotor COMMAND test_cpp-rotor)
