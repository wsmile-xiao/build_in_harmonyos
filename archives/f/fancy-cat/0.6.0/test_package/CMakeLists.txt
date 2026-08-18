cmake_minimum_required(VERSION 3.15)
project(test_package LANGUAGES C)

# fancy-cat 是 Zig 应用（application），无 C 库可链接到 test；
# CMakeLists.txt 满足 L0c 门禁（test_package 必须有 test 源文件）。
# 真实验证在 test_package/conanfile.py test() 中经 self.run() 执行
# fancy-cat --version（L0d/R34），test_fancy_cat.c 通过 system() 调用亦具独立验证能力。
add_executable(test_fancy_cat test_fancy_cat.c)
