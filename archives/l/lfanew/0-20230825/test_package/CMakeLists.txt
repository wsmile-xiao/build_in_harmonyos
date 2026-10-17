cmake_minimum_required(VERSION 3.15)
project(test_lfanew C)

find_package(lfanew REQUIRED CONFIG)

add_executable(test_lfanew test_lfanew.c)
target_link_libraries(test_lfanew PRIVATE lfanew::lfanew)
# libc-only consumer: static link so it also runs under qemu-aarch64 on
# x86_64 runners where the OHOS musl loader is absent (E544).
target_link_options(test_lfanew PRIVATE -static)
