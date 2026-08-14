cmake_minimum_required(VERSION 3.15)
project(test_mongoc C CXX)

find_package(mongoc-driver REQUIRED)

add_executable(test_mongoc test_mongoc.cpp)
target_link_libraries(test_mongoc mongoc-driver::mongoc-driver)

enable_testing()
add_test(NAME test_mongoc COMMAND test_mongoc)
