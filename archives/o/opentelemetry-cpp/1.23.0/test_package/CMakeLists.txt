cmake_minimum_required(VERSION 3.16)
project(test_opentelemetry_cpp LANGUAGES CXX)

find_package(opentelemetry-cpp CONFIG REQUIRED COMPONENTS api)

add_executable(test_api test_api.cpp)
target_compile_features(test_api PRIVATE cxx_std_17)
target_link_libraries(test_api PRIVATE opentelemetry-cpp::api)
