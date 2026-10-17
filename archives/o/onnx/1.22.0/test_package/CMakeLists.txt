cmake_minimum_required(VERSION 3.16)
project(test_onnx LANGUAGES CXX)

find_package(Protobuf CONFIG REQUIRED)
find_package(onnx CONFIG REQUIRED)

add_executable(test_onnx test_onnx.cpp)
target_compile_features(test_onnx PRIVATE cxx_std_17)
target_link_libraries(test_onnx PRIVATE ONNX::onnx protobuf::libprotobuf)

enable_testing()
add_test(NAME onnx_minimal_model COMMAND test_onnx)
