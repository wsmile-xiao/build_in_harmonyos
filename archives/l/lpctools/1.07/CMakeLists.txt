cmake_minimum_required(VERSION 3.16)
project(lpctools C)

# 上游 Makefile 用三组**互不相同**的对象集建三个可执行文件：
#
#   lpcisp          = lpcisp.o   + isp_utils.o + isp_commands.o + isp_wrapper.o
#   lpcprog         = lpcprog.o  + isp_utils.o + isp_commands.o + prog_commands.o + parts.o
#   lpc_binary_check= check.o    + isp_utils.o
#
# ★ check.c 自带 main()，是独立的自检程序，**不能**和 lpcprog/lpcisp 一起链
#   —— 混链会得到 ld.lld: duplicate symbol: main / help / trace_on。
#   这正是上游把对象集拆成三组的原因，这里如实照搬。
#
# 三段必须分开写：CMake 不支持 ${${t}_SRC} 这种间接变量展开。
add_executable(lpcisp   lpcisp.c   isp_utils.c isp_commands.c isp_wrapper.c)
add_executable(lpcprog  lpcprog.c  isp_utils.c isp_commands.c prog_commands.c parts.c)
add_executable(lpc_binary_check check.c isp_utils.c)

foreach(t lpcisp lpcprog lpc_binary_check)
    target_compile_options(${t} PRIVATE -w)
    target_compile_options(${t} PRIVATE -O2)
    set_property(TARGET ${t} PROPERTY C_STANDARD 99)
    set_target_properties(${t} PROPERTIES
        RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}")
endforeach()
