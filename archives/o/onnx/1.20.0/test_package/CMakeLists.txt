cmake_minimum_required(VERSION 3.15)
project(test_onnx CXX)

# ONNX installs its own ONNXConfig.cmake (namespace ONNX::)
find_package(ONNX REQUIRED CONFIG)
# Consumers must also link protobuf explicitly (same as upstream onnx/test/cmake)
find_package(Protobuf REQUIRED CONFIG)

add_executable(test_onnx test_onnx.cpp)
target_link_libraries(test_onnx PRIVATE ONNX::onnx protobuf::libprotobuf)

include(CTest)
add_test(NAME test_onnx COMMAND test_onnx)
