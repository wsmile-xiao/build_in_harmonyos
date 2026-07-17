cmake_minimum_required(VERSION 3.15)
project(test_uvwasi C)

# uvwasi.h 公开 include 了 libuv 的 uv.h，故消费者需同时拿到 libuv 头文件/库。
find_package(uvwasi REQUIRED)
find_package(libuv REQUIRED)

add_executable(test_uvwasi test.c)
target_link_libraries(test_uvwasi uvwasi::uvwasi libuv::libuv)

enable_testing()
add_test(NAME test_uvwasi COMMAND test_uvwasi)
