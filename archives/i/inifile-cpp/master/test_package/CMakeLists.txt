cmake_minimum_required(VERSION 3.15)
project(inifile_cpp_upstream_tests LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 11)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(Catch2 CONFIG REQUIRED)

add_executable(unit_tests
    upstream_tests/main.cpp
    upstream_tests/test_inifile.cpp
)

target_include_directories(unit_tests PRIVATE
    "${INIFILE_INCLUDE_DIR}"
    "${CMAKE_CURRENT_SOURCE_DIR}"
    "${CMAKE_CURRENT_SOURCE_DIR}/upstream_tests"
)

target_link_libraries(unit_tests PRIVATE Catch2::Catch2)

target_compile_options(unit_tests PRIVATE -Wall -Wextra)
