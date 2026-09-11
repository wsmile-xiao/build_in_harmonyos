cmake_minimum_required(VERSION 3.15)
project(test_sherpa_onnx C)

find_package(sherpa-onnx REQUIRED)

add_executable(test_sherpa_onnx test_sherpa_onnx.c)
target_link_libraries(test_sherpa_onnx PRIVATE sherpa-onnx::sherpa-onnx-c-api)
