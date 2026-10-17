cmake_minimum_required(VERSION 3.16)
project(test_pm_utils C)

add_executable(test_pm_utils test_pm_utils.c)

# argv[1] 由 conan test() 传入（包根目录），配置期不可知，故不注册 add_test。
