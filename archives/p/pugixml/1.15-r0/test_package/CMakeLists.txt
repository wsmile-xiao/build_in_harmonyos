cmake_minimum_required(VERSION 3.15)
project(test_pugixml CXX)

# Find the package via Conan-generated CMakeDeps
find_package(pugixml REQUIRED)

add_executable(test_pugixml test.cpp)
target_link_libraries(test_pugixml pugixml::pugixml)

enable_testing()
add_test(NAME test_pugixml COMMAND test_pugixml)