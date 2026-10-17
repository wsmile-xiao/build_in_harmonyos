cmake_minimum_required(VERSION 3.15)
project(test_torsocks C)

add_executable(test_torsocks test.c)
# dlopen/dlsym 在 OHOS musl 的 libc 中（CMAKE_DL_LIBS 为空），无需显式 -ldl
target_link_libraries(test_torsocks PRIVATE ${CMAKE_DL_LIBS})
