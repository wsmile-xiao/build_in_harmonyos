cmake_minimum_required(VERSION 3.15)
project(test_kidletime CXX)

find_package(KF6IdleTime REQUIRED)

add_executable(test_kidletime test.cpp)
target_link_libraries(test_kidletime KF6::IdleTime)

enable_testing()
add_test(NAME test_kidletime COMMAND test_kidletime)
