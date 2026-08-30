cmake_minimum_required(VERSION 3.15)
project(test_libsvm CXX)

find_package(libsvm REQUIRED)

add_executable(test_libsvm test_libsvm.cpp)
target_link_libraries(test_libsvm libsvm::libsvm)
