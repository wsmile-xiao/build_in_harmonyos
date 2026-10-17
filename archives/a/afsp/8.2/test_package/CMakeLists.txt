cmake_minimum_required(VERSION 3.15)
project(test_package LANGUAGES C)

# afsp 是音频工具集（application），无 C 库可链接到 test；
# CMakeLists.txt 满足 L0c 门禁（test_package 必须有 test 源文件）。
# 真实验证在 test_package/conanfile.py test() 中通过 subprocess 完成
# （执行 InfoAudio --help，R34 反空壳）。
add_executable(test_afsp test_afsp.c)
