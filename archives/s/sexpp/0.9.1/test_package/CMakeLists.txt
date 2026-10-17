cmake_minimum_required(VERSION 3.15)
project(test_sexpp CXX)

# Find the package via Conan-generated CMakeDeps
find_package(sexpp REQUIRED)

add_executable(test_sexpp test.cpp)
target_link_libraries(test_sexpp sexpp::sexpp)
target_compile_features(test_sexpp PRIVATE cxx_std_11)

enable_testing()
add_test(NAME test_sexpp COMMAND test_sexpp)
