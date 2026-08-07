cmake_minimum_required(VERSION 3.15)
project(test_package C CXX)

find_package(ada-url REQUIRED)

add_executable(test_ada test.cpp)
target_link_libraries(test_ada PRIVATE ada-url::ada-url)
set_property(TARGET test_ada PROPERTY CXX_STANDARD 20)