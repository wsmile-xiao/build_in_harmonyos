cmake_minimum_required(VERSION 3.15)
project(test_g3log CXX)

# Find the package via Conan-generated CMakeDeps
find_package(g3log REQUIRED)

add_executable(test_g3log test.cpp)
target_link_libraries(test_g3log g3log::g3log)

enable_testing()
add_test(NAME test_g3log COMMAND test_g3log)