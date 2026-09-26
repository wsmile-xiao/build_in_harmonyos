cmake_minimum_required(VERSION 3.15)
project(test_irstlm CXX)

# Find the package via Conan-generated CMakeDeps
find_package(irstlm REQUIRED)

add_executable(test_irstlm test.cpp)
target_link_libraries(test_irstlm irstlm::irstlm)

enable_testing()
add_test(NAME test_irstlm COMMAND test_irstlm)
