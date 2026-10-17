cmake_minimum_required(VERSION 3.15)
project(dsp_test LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 11)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

find_package(signalsmith-dsp CONFIG REQUIRED)

add_executable(dsp_test test.cpp)
target_link_libraries(dsp_test PRIVATE signalsmith-dsp)

enable_testing()
add_test(NAME dsp_test COMMAND dsp_test)
