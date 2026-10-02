cmake_minimum_required(VERSION 3.15)
# CXX 启用：whole-archive 收录的 libsems_core.a 是 C++ 静态库，宿主
# 链接需 C++ 运行时（libc++），纯 C 工程链接器不带（vtable 未定义根因）
project(test_sems-dsm C CXX)

# 消费路径：dlopen 插件动态模块（SEMS 插件加载模型——插件引用宿主符号）。
# dsm.so 引用 420 个 core 符号（AmMutex/AmMimeBody/AmPlaylist 等，llvm-nm
# 实测）。INTERFACE 目标会被 CMake 排出 whole-archive 包裹范围，故按绝对
# 路径显式全量收录随包 libsems_core.a/libsems_sip.a（路径由 test_package
# conanfile 以 -D 变量注入），-rdynamic 导出供 dsm.so 重定位。
find_package(sems-dsm REQUIRED)

# resample.cpp 被上游 target_sources 只挂到 sems/sems_tests 可执行目标，
# 不在 libsems_core.a 内——宿主直接编译随包分发的 resample 源码补齐
# ResampleFactory 符号
file(GLOB RESAMPLE_SRC "${SEMS_RESAMPLE_SRC}/*.cpp")

add_executable(test_sems-dsm test.c ${RESAMPLE_SRC})
# SEMS 插件加载模型：宿主（sems 主程序）以 -rdynamic 导出 core 符号供
# dlopen 插件重定位，测试宿主同样需要导出
target_link_options(test_sems-dsm PRIVATE -rdynamic)
target_include_directories(test_sems-dsm PRIVATE sems-dsm::sems-dsm)
target_link_libraries(test_sems-dsm
    -Wl,--whole-archive ${SEMS_CORE_A} ${SEMS_SIP_A} -Wl,--no-whole-archive
    ${LIBEVENT_A}
    ${CMAKE_DL_LIBS})
# 源文件为 .c，默认链接器语言是 C（不带 libc++）；强制 CXX 链接器
set_target_properties(test_sems-dsm PROPERTIES LINKER_LANGUAGE CXX)

enable_testing()
add_test(NAME test_sems-dsm COMMAND test_sems-dsm)
