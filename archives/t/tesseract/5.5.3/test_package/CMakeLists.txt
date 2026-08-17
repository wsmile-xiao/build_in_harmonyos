cmake_minimum_required(VERSION 3.15)
project(test_tesseract CXX)

# Find the package via Conan-generated CMakeDeps
find_package(tesseract REQUIRED)

add_executable(test_tesseract test.cpp)
target_link_libraries(test_tesseract tesseract::tesseract)

enable_testing()
add_test(NAME test_tesseract COMMAND test_tesseract)
