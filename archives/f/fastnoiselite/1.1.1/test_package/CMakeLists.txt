cmake_minimum_required(VERSION 3.15)
project(test_fastnoiselite CXX)

# Find the package via Conan-generated CMakeDeps
find_package(fastnoiselite REQUIRED)

add_executable(test_fastnoiselite test.cpp)
target_link_libraries(test_fastnoiselite fastnoiselite::fastnoiselite)

enable_testing()
add_test(NAME test_fastnoiselite COMMAND test_fastnoiselite)