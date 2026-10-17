cmake_minimum_required(VERSION 3.15)
project(jaula_test_package CXX)

# 强制 C++11：jaula 的 9 个公开头共 13 处使用动态异常规范（如
# `Value const &) throw(Bad_Data_Type)`），该语法在 C++17 已被移除，
# 用 C++17 及以上编译任何包含 <jaula.h> 的消费者都会失败。
set(CMAKE_CXX_STANDARD 11)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

find_package(jaula REQUIRED CONFIG)

foreach(case_name test_parse test_corpus test_errors)
  add_executable(${case_name} ${case_name}.cpp)
  target_link_libraries(${case_name} PRIVATE jaula::jaula)
  target_include_directories(${case_name} PRIVATE ${CMAKE_CURRENT_LIST_DIR})
endforeach()
