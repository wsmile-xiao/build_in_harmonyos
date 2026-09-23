cmake_minimum_required(VERSION 3.15)
project(test_cppdb CXX)
set(CMAKE_CXX_STANDARD 14)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(cppdb REQUIRED CONFIG)

# Consumer test: link the packaged library and use its public API.
add_executable(test_cppdb test.cpp)
target_link_libraries(test_cppdb PRIVATE cppdb::cppdb)

# Upstream replay: reimplements the sqlite paths of upstream
# test_basic.cpp / test_backend.cpp without a DB server.
add_executable(test_cppdb_upstream test_upstream.cpp)
target_link_libraries(test_cppdb_upstream PRIVATE cppdb::cppdb)

enable_testing()
add_test(NAME test_cppdb COMMAND test_cppdb)
add_test(NAME test_cppdb_upstream COMMAND test_cppdb_upstream)
