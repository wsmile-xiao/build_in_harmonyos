cmake_minimum_required(VERSION 3.15)
project(test_libdart CXX)

set(CMAKE_CXX_STANDARD 14)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Find the package via Conan-generated CMakeDeps
find_package(libdart REQUIRED)
find_package(RapidJSON REQUIRED)

add_executable(test_libdart test.cpp)
target_link_libraries(test_libdart libdart::libdart RapidJSON::RapidJSON)
# Enable libdart's RapidJSON-backed parse/serialize feature.
target_compile_definitions(test_libdart PRIVATE DART_HAS_RAPIDJSON=1)

enable_testing()
add_test(NAME test_libdart COMMAND test_libdart)