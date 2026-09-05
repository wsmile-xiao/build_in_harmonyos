cmake_minimum_required(VERSION 3.15)
project(test_libfork CXX)

# Find the package via Conan-generated CMakeDeps
find_package(libfork REQUIRED)

add_executable(test_libfork test_libfork.cpp)
target_link_libraries(test_libfork libfork::libfork)
target_compile_features(test_libfork PRIVATE cxx_std_23)

enable_testing()
add_test(NAME test_libfork COMMAND test_libfork)
