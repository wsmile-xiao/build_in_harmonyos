cmake_minimum_required(VERSION 3.15)
project(test_simbody CXX)

# Find the package via Conan-generated CMakeDeps
find_package(simbody REQUIRED)

add_executable(test_simbody test.cpp)
target_link_libraries(test_simbody simbody::simbody)
set_target_properties(test_simbody PROPERTIES CXX_STANDARD 17)
target_link_libraries(test_simbody m)

enable_testing()
add_test(NAME test_simbody COMMAND test_simbody)