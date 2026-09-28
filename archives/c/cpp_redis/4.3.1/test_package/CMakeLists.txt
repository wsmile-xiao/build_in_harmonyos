cmake_minimum_required(VERSION 3.15)
project(test_cpp_redis CXX)

# Find the package via Conan-generated CMakeDeps
find_package(cpp_redis REQUIRED)

add_executable(test_cpp_redis test.cpp)
target_link_libraries(test_cpp_redis cpp_redis::cpp_redis)
target_compile_features(test_cpp_redis PRIVATE cxx_std_11)

enable_testing()
add_test(NAME test_cpp_redis COMMAND test_cpp_redis)