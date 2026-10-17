cmake_minimum_required(VERSION 3.24)
project(test_falcosecurity_libs LANGUAGES CXX)

find_package(falcosecurity-libs CONFIG REQUIRED)

add_executable(test_falcosecurity_libs test_falcosecurity_libs.cpp)
target_link_libraries(test_falcosecurity_libs PRIVATE falcosecurity-libs::falcosecurity-libs)
