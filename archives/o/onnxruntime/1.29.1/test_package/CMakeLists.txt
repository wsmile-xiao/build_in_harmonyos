cmake_minimum_required(VERSION 3.28)
project(test_onnxruntime CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(onnxruntime REQUIRED)

enable_testing()
add_executable(test_onnxruntime test_onnxruntime.cpp)
target_link_libraries(test_onnxruntime onnxruntime::onnxruntime)
add_test(NAME onnxruntime_test COMMAND test_onnxruntime)
