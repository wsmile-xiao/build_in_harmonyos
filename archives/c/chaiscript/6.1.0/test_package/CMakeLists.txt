cmake_minimum_required(VERSION 3.15)
project(test_package CXX)

find_package(Threads REQUIRED)
find_package(chaiscript REQUIRED)

add_executable(test_chaiscript test.cpp)
# dladdr() 用于模块搜索路径探测（OHOS musl 中位于 libc，CMAKE_DL_LIBS 空链接无害）
target_link_libraries(test_chaiscript PRIVATE
    chaiscript::chaiscript Threads::Threads ${CMAKE_DL_LIBS})
set_property(TARGET test_chaiscript PROPERTY CXX_STANDARD 14)
set_property(TARGET test_chaiscript PROPERTY CXX_STANDARD_REQUIRED ON)
