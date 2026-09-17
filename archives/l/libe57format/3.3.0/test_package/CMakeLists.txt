cmake_minimum_required(VERSION 3.15)
project(e57_consumer CXX)

set(CMAKE_CXX_STANDARD 14)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# Consumer links the installed libe57format package (Conan CMakeDeps).
find_package(e57format CONFIG REQUIRED)

add_executable(test_version test_version.cpp)
target_link_libraries(test_version PRIVATE E57Format)

add_executable(test_roundtrip test_roundtrip.cpp)
target_link_libraries(test_roundtrip PRIVATE E57Format)

enable_testing()
add_test(NAME test_version COMMAND test_version)
add_test(NAME test_roundtrip COMMAND test_roundtrip)
