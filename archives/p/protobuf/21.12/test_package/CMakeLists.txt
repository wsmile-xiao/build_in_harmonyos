cmake_minimum_required(VERSION 3.16)
project(test_protobuf LANGUAGES CXX)

find_package(Protobuf CONFIG REQUIRED)

add_executable(test_protobuf test_protobuf.cpp)
target_compile_features(test_protobuf PRIVATE cxx_std_17)
target_link_libraries(test_protobuf PRIVATE protobuf::libprotobuf)

enable_testing()
foreach(test_case dynamic pool arena parse_error)
  add_test(NAME protobuf_${test_case} COMMAND test_protobuf ${test_case})
endforeach()
add_test(NAME protobuf_protoc_version COMMAND protobuf::protoc --version)
