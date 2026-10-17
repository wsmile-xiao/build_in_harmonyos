cmake_minimum_required(VERSION 3.16)
project(test_dds2tar C)

add_executable(test_dds2tar test_dds2tar.c)

# argv[1..3] 由 conan test() 阶段传入（包内已安装的三个产物路径），配置期不可知，故不注册 add_test。
