cmake_minimum_required(VERSION 3.15)
project(test_log4cxx CXX)

# Find the package via Conan-generated CMakeDeps
find_package(log4cxx CONFIG REQUIRED)

add_executable(test_log4cxx test.cpp)
target_link_libraries(test_log4cxx log4cxx::log4cxx)

enable_testing()
add_test(NAME test_log4cxx COMMAND test_log4cxx)
