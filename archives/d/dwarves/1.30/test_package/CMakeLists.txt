cmake_minimum_required(VERSION 3.15)
project(dwarves_test_package C)

find_package(dwarves CONFIG REQUIRED)
# dwarves.h（dwarves 安装的公开头）第 14-16 行直接 #include <obstack.h>/
# <dwarf.h>/<elfutils/libdwfl.h>，OHOS-musl 下由 musl-obstack 与 elfutils 提供；
# CMakeDeps 对传递依赖不展开 include 元数据，消费者为编译 dwarves 公开头
# 需显式链接这些垫片/依赖 target（真实上游依赖解析）。
find_package(musl-obstack CONFIG REQUIRED)
find_package(argp-standalone CONFIG REQUIRED)
find_package(elfutils CONFIG REQUIRED)

add_executable(consumer_dwarves consumer_dwarves.c)
target_link_libraries(consumer_dwarves PRIVATE dwarves::dwarves)
target_link_libraries(consumer_dwarves PRIVATE musl-obstack::musl-obstack argp-standalone::argp-standalone elfutils::elfutils)