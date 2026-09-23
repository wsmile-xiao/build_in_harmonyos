cmake_minimum_required(VERSION 3.15)
project(test_flatbuffers CXX)

find_package(flatbuffers REQUIRED)

add_executable(test_flatbuffers test.cpp)
target_link_libraries(test_flatbuffers PRIVATE flatbuffers::flatbuffers)
target_compile_features(test_flatbuffers PRIVATE cxx_std_17)

enable_testing()
add_test(NAME test_flatbuffers COMMAND test_flatbuffers)
