cmake_minimum_required(VERSION 3.16)
project(test_cpmtools C)

add_executable(test_cpmtools test_cpmtools.c)

# argv[1] 由 conan test() 传入（包内 bin 目录），配置期不可知，故不注册 add_test。