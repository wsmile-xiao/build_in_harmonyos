cmake_minimum_required(VERSION 3.15)
project(test_tao_pegtl CXX)

# Find the package via Conan-generated CMakeDeps
find_package(tao-pegtl REQUIRED)

add_executable(test_tao_pegtl test.cpp)
target_link_libraries(test_tao_pegtl tao-pegtl::tao-pegtl)

enable_testing()
add_test(NAME test_tao_pegtl COMMAND test_tao_pegtl)