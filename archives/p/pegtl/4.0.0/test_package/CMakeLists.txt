cmake_minimum_required(VERSION 3.15)
project(test_pegtl CXX)

# Find the package via Conan-generated CMakeDeps
find_package(pegtl REQUIRED)

add_executable(test_pegtl test_package_consumer.cpp)
target_link_libraries(test_pegtl pegtl::pegtl)
set_target_properties(test_pegtl PROPERTIES CXX_STANDARD 17 CXX_STANDARD_REQUIRED ON)

enable_testing()
add_test(NAME test_pegtl COMMAND test_pegtl)