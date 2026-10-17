cmake_minimum_required(VERSION 3.15)
# 编译器 / CMAKE_SYSTEM_PROCESSOR 由 Conan 生成的 CMakeToolchain 提供，
# 这里不覆盖 CMAKE_SYSTEM_NAME（OHOS profile 不能被伪装成 Linux）。
project(test_liborigin2 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

find_package(liborigin2 REQUIRED CONFIG)

# liborigin2 的公共头直接 include 这两者的头文件，消费者必须自己找到它们：
#   OriginObj.h    → boost/variant.hpp, boost/bind.hpp, boost/date_time/...
#   OriginParser.h → tree.hh
# 这也是本 test_package 同时声明 boost / tree-hh 两个 require 的原因。
find_package(Boost REQUIRED CONFIG)
find_package(tree-hh REQUIRED CONFIG)

add_executable(test_origin2 test_origin2.cpp)
target_link_libraries(test_origin2 PRIVATE
    liborigin2::liborigin2
    Boost::headers
    tree-hh::tree-hh)

enable_testing()
add_test(NAME test_origin2 COMMAND test_origin2)
