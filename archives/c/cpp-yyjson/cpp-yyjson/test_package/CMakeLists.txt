cmake_minimum_required(VERSION 3.16)
project(test_cpp_yyjson LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

find_package(cpp_yyjson CONFIG REQUIRED)

add_executable(test_cpp_yyjson test.cpp)
target_link_libraries(test_cpp_yyjson PRIVATE cpp_yyjson::cpp_yyjson)

add_executable(test_ohos_special test_ohos_special.cpp)
target_link_libraries(test_ohos_special PRIVATE cpp_yyjson::cpp_yyjson)
