cmake_minimum_required(VERSION 3.16)
project(test_grantleetheme LANGUAGES CXX)

include(${CMAKE_BINARY_DIR}/conan_toolchain.cmake OPTIONAL)
include(${CMAKE_BINARY_DIR}/conan_cmakedeps_paths.cmake OPTIONAL)

find_package(Qt6 REQUIRED COMPONENTS Core)
find_package(KPim6GrantleeTheme CONFIG REQUIRED)

add_executable(test_grantleetheme test_package.cpp)
target_link_libraries(test_grantleetheme PRIVATE Qt6::Core KPim6::GrantleeTheme)

enable_testing()
add_test(NAME test_grantleetheme COMMAND test_grantleetheme)
