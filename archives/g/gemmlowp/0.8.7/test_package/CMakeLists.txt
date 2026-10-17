cmake_minimum_required(VERSION 3.15)
project(test_gemmlowp CXX)

# Find the package via Conan-generated CMakeDeps
find_package(gemmlowp REQUIRED)

add_executable(test_gemmlowp test.cc)
target_link_libraries(test_gemmlowp gemmlowp::gemmlowp)

enable_testing()
add_test(NAME test_gemmlowp COMMAND test_gemmlowp)
