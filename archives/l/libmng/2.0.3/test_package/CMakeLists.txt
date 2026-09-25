cmake_minimum_required(VERSION 3.16)
project(test_package C)

find_package(libmng REQUIRED CONFIG)
# zlib 是 libmng 的 public 依赖(头文件传播, transitive_headers), 测试
# 程序化构造 MNG 流时直接调用 crc32/compress2, 故显式链接。
find_package(zlib REQUIRED CONFIG)

add_executable(test_package test_package.c)
target_link_libraries(test_package PRIVATE libmng::libmng zlib::zlib)
