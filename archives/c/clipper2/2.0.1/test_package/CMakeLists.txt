cmake_minimum_required(VERSION 3.15)
project(test_clipper2 CXX)

find_package(Clipper2 REQUIRED)

add_executable(test_clipper2 test_clipper2.cpp)
target_link_libraries(test_clipper2 PRIVATE Clipper2::Clipper2)
