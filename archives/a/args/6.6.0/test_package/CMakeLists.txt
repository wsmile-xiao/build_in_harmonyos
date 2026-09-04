cmake_minimum_required(VERSION 3.15)
project(test_package_args CXX)

find_package(args REQUIRED)

add_executable(test_package_args test_package_args.cpp)
target_link_libraries(test_package_args PRIVATE taywee::args)
set_target_properties(test_package_args PROPERTIES CXX_STANDARD 11)