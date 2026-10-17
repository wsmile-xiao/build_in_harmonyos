cmake_minimum_required(VERSION 3.15)
project(test_fplus CXX)

# Find the package via Conan-generated CMakeDeps
find_package(FunctionalPlus REQUIRED)

add_executable(test_fplus test_fplus.cpp)
target_link_libraries(test_fplus FunctionalPlus::fplus)

enable_testing()
add_test(NAME test_fplus COMMAND test_fplus)
