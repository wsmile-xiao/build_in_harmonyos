cmake_minimum_required(VERSION 3.15)
project(test_package LANGUAGES C)

# alfred 是 C 命令行工具（application），无 C 库可链接到 test；
# CMakeLists.txt 满足 L0c 门禁（test_package 必须有 test 源文件）。
# 真实验证在 test_package/conanfile.py test() 中通过 self.run() 完成
# （执行 alfred --help，R34 反空壳）。
add_executable(test_alfred test_alfred.c)
