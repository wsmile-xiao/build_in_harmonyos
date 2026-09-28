cmake_minimum_required(VERSION 3.15)
project(test_libnpy CXX)

# Find the package via Conan-generated CMakeDeps
find_package(libnpy REQUIRED)

add_executable(test_libnpy test.cpp)
target_link_libraries(test_libnpy libnpy::libnpy)
target_compile_features(test_libnpy PRIVATE cxx_std_14)

enable_testing()
add_test(NAME test_libnpy COMMAND test_libnpy)
