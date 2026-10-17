cmake_minimum_required(VERSION 3.5)
project(test_asyncplusplus CXX)

find_package(Async++ REQUIRED)

add_executable(test_asyncplusplus test_asyncplusplus.cpp)
target_link_libraries(test_asyncplusplus PRIVATE Async++)
set_target_properties(test_asyncplusplus PROPERTIES CXX_STANDARD 11)
