cmake_minimum_required(VERSION 3.20)
project(test_lldb_consumer LANGUAGES CXX)

# 直接使用 conan test_package generate() 传入的包内路径，
# 不依赖 find_package（本包为 application 型，不生成 CMake config）。
add_executable(test_lldb_consumer test_consumer.cpp)
target_include_directories(test_lldb_consumer PRIVATE ${LLDB_INCLUDE_DIR})
target_link_directories(test_lldb_consumer PRIVATE ${LLDB_LIB_DIR})
target_link_libraries(test_lldb_consumer PRIVATE lldb)

# C3 按名断点（BreakpointCreateByName("main")）需要测试目标带调试信息：
# CI profile build_type=Release 默认无 -g，显式为这个小测试目标开启
# （不影响主包构建，仅 test_package 单 TU）
target_compile_options(test_lldb_consumer PRIVATE -g)
