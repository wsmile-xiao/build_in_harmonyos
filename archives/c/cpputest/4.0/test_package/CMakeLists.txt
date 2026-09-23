cmake_minimum_required(VERSION 3.15)
project(cpputest_consumer_test LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 11)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(cpputest REQUIRED)

add_executable(cpputest_consumer_test consumer_test.cpp)
target_link_libraries(cpputest_consumer_test PRIVATE cpputest::cpputest)
