cmake_minimum_required(VERSION 3.15)
project(test_flagpp CXX)

# Find the package via Conan-generated CMakeDeps
find_package(flagpp REQUIRED)

add_executable(test_flagpp test.cpp)
target_link_libraries(test_flagpp flagpp::flagpp)
target_compile_features(test_flagpp PRIVATE cxx_std_23)

enable_testing()
add_test(NAME test_flagpp COMMAND test_flagpp)