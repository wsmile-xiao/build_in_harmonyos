cmake_minimum_required(VERSION 3.15)
project(test_frameofreference CXX)

# Find the package via Conan-generated CMakeDeps
find_package(frameofreference REQUIRED)

add_executable(test_frameofreference test.cpp)
target_link_libraries(test_frameofreference frameofreference::frameofreference)
target_compile_features(test_frameofreference PRIVATE cxx_std_11)

enable_testing()
add_test(NAME test_frameofreference COMMAND test_frameofreference)
