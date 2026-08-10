cmake_minimum_required(VERSION 3.15)
project(test_package LANGUAGES C)

# iortcw is a C application (make build), no C library to link.
# test_iortcw.c 满足 L0c 门禁（test_package 必须有 test 源文件）；
# 真实验证在 test_package/conanfile.py test() 方法中通过 self.run() 完成。
add_executable(test_iortcw test_iortcw.c)
