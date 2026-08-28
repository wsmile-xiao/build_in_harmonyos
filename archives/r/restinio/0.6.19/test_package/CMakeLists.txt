cmake_minimum_required(VERSION 3.5)
project(restinio_test CXX)

set(CMAKE_CXX_STANDARD 14)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(restinio REQUIRED)
find_package(fmt REQUIRED)
find_package(http_parser REQUIRED)

add_executable(restinio_test restinio_test.cpp)
target_link_libraries(restinio_test PRIVATE restinio::restinio fmt::fmt http_parser::http_parser)
target_compile_definitions(restinio_test PRIVATE ASIO_STANDALONE ASIO_HAS_STD_CHRONO ASIO_DISABLE_STD_STRING_VIEW)
