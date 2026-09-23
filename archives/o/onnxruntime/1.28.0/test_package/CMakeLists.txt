cmake_minimum_required(VERSION 3.15)
project(test_onnxruntime CXX)

find_package(onnxruntime REQUIRED)

enable_testing()
add_executable(test_onnxruntime test_onnxruntime.cpp)
target_link_libraries(test_onnxruntime onnxruntime::onnxruntime)
add_test(NAME onnxruntime_test COMMAND test_onnxruntime)
