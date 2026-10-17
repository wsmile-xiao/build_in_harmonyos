cmake_minimum_required(VERSION 3.15)
project(metaeuk_consumer LANGUAGES CXX)

add_executable(metaeuk_consumer consumer.cpp)

if(NOT WIN32)
    target_compile_options(metaeuk_consumer PRIVATE -std=c++11)
endif()

enable_testing()
add_test(NAME metaeuk_consumer COMMAND metaeuk_consumer)
