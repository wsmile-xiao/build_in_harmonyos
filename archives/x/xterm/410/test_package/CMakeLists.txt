# xterm 是终端工具（非库），不需要 CMake 构建测试
# test_package/conanfile.py 直接验证二进制存在
cmake_minimum_required(VERSION 3.15)
project(test_xterm)
