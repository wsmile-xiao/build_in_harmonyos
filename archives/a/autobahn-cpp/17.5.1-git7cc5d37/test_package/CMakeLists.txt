cmake_minimum_required(VERSION 3.15)
project(test_autobahn_cpp CXX)

find_package(autobahn-cpp CONFIG REQUIRED)

add_executable(test_autobahn_cpp test.cpp)
target_link_libraries(test_autobahn_cpp PRIVATE autobahn-cpp::autobahn-cpp)

enable_testing()
add_test(NAME test_autobahn_cpp COMMAND test_autobahn_cpp)
