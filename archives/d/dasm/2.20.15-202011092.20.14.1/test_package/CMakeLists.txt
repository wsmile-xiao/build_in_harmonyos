cmake_minimum_required(VERSION 3.16)
project(test_dasm C)

add_executable(test_dasm test_dasm.c test_cases.h)
target_include_directories(test_dasm PRIVATE ${CMAKE_CURRENT_SOURCE_DIR})

# argv[1] 由 conan test() 传入（包根目录），配置期不可知，故不注册 add_test。
