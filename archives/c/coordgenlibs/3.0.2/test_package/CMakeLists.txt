cmake_minimum_required(VERSION 3.15)
project(test_coordgenlibs CXX)

set(CMAKE_CXX_STANDARD 11)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Find the package via Conan-generated CMakeDeps
find_package(coordgenlibs REQUIRED)

add_executable(test_coordgenlibs test.cpp)
target_link_libraries(test_coordgenlibs coordgenlibs::coordgenlibs)

# HarmonyOS-specific verification test (2D coordinate generation on OHOS)
add_executable(test_coordgen_hmos test_coordgen_hmos.cpp)
target_link_libraries(test_coordgen_hmos coordgenlibs::coordgenlibs)

enable_testing()
add_test(NAME test_coordgenlibs COMMAND test_coordgenlibs)
add_test(NAME test_coordgen_hmos COMMAND test_coordgen_hmos)
