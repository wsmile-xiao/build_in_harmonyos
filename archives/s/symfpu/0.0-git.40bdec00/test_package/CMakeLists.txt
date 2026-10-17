cmake_minimum_required(VERSION 3.15)
project(test_symfpu CXX)

# Find the package via Conan-generated CMakeDeps
find_package(symfpu REQUIRED)

add_executable(test_symfpu test.cpp)
target_link_libraries(test_symfpu symfpu::symfpu)

enable_testing()
add_test(NAME test_symfpu COMMAND test_symfpu)