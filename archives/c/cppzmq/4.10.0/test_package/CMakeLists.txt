cmake_minimum_required(VERSION 3.15)
project(test_cppzmq CXX)

find_package(cppzmq REQUIRED)
find_package(ZeroMQ REQUIRED)

add_executable(test_cppzmq test_cppzmq.cpp)
target_link_libraries(test_cppzmq PRIVATE cppzmq libzmq)
target_compile_features(test_cppzmq PRIVATE cxx_std_11)

enable_testing()
add_test(NAME test_cppzmq COMMAND test_cppzmq)
