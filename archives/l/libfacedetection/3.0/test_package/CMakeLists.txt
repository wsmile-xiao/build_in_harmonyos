cmake_minimum_required(VERSION 3.15)
project(test_libfacedetection CXX)

# Find the package via Conan-generated CMakeDeps
find_package(facedetection REQUIRED)

add_executable(test_libfacedetection test.cpp)
target_link_libraries(test_libfacedetection facedetection)

enable_testing()
add_test(NAME test_libfacedetection COMMAND test_libfacedetection)
