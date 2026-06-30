cmake_minimum_required(VERSION 3.15)
project(test_libqxp CXX)

set(CMAKE_CXX_STANDARD 17)

# Find the package via Conan-generated CMakeDeps
find_package(libqxp REQUIRED)
find_package(librevenge REQUIRED)

add_executable(test_libqxp test.cpp)
target_link_libraries(test_libqxp libqxp::libqxp librevenge::librevenge librevenge::stream)

enable_testing()
add_test(NAME test_libqxp COMMAND test_libqxp)
