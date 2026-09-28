cmake_minimum_required(VERSION 3.15)
project(test_frugally-deep CXX)

# Find the package via Conan-generated CMakeDeps
find_package(frugally-deep REQUIRED)

add_executable(test_frugally-deep test_frugally_deep.cpp)
target_link_libraries(test_frugally-deep frugally-deep::frugally-deep)

enable_testing()
add_test(NAME test_frugally-deep COMMAND test_frugally-deep)