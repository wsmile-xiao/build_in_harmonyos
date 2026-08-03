cmake_minimum_required(VERSION 3.15)
project(test_openal C CXX)

find_package(OpenAL REQUIRED CONFIG)

add_executable(upstream_basic upstream_basic.cpp)
target_link_libraries(upstream_basic PRIVATE OpenAL::OpenAL)

add_executable(test_openal_null_backend test_openal.c)
set_property(TARGET test_openal_null_backend PROPERTY LINKER_LANGUAGE CXX)
target_link_libraries(test_openal_null_backend PRIVATE OpenAL::OpenAL)
