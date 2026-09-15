cmake_minimum_required(VERSION 3.15)
project(test_metrohash CXX)

# Find the package via Conan-generated CMakeDeps
find_package(metrohash REQUIRED)

add_executable(test_metrohash test_metrohash.cpp)
target_link_libraries(test_metrohash metrohash::metrohash)
set_target_properties(test_metrohash PROPERTIES CXX_STANDARD 11)

enable_testing()
add_test(NAME test_metrohash COMMAND test_metrohash)
