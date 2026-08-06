cmake_minimum_required(VERSION 3.15)
project(test_glm CXX)

# Find the package via Conan-generated CMakeDeps
find_package(glm REQUIRED)

add_executable(test_glm test.cpp)
target_link_libraries(test_glm glm::glm)

enable_testing()
add_test(NAME test_glm COMMAND test_glm)
