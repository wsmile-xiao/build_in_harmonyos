cmake_minimum_required(VERSION 3.16)
project(test_seriation C)

add_executable(test_seriation test_seriation.c)

# argv[1] 由 conan test() 传入（包根目录），配置期不可知，故不注册 add_test。
