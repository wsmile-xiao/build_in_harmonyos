cmake_minimum_required(VERSION 3.15)
project(test_access_profiler CXX)

# Find the package via Conan-generated CMakeDeps
find_package(access_profiler REQUIRED)

add_executable(test_access_profiler test.cpp)
target_link_libraries(test_access_profiler access_profiler::access_profiler)
target_compile_features(test_access_profiler PRIVATE cxx_std_17)

enable_testing()
add_test(NAME test_access_profiler COMMAND test_access_profiler)
