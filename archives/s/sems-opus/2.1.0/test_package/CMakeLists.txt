cmake_minimum_required(VERSION 3.15)
project(test_sems-opus C)

# 消费路径：dlopen 插件动态模块（SEMS 插件加载模型——插件引用宿主的
# 日志符号）。opus.so 实际仅引用 4 个 core 日志符号（llvm-nm 实测），
# 测试宿主内联提供，避免 whole-archive 拉入全部 core 及其 libevent 依赖。
find_package(sems-opus REQUIRED)

# 头文件 ABI：test.c 直接包含包内 sems/amci/amci.h 与 sems/amci/codecs.h
# （上游真实导出结构定义）。该 include 目录由 conanfile 在 configure 阶段
# 从依赖包 cpp_info 注入——不能写 `sems-opus::sems-opus`：CMake 不解析
# `pkg::pkg` 形式的导入目标名，会把它当成相对路径拼进 -I。
# SEMS_OPUS_PLUGIN 为被测插件绝对路径（lib/sems/plug-in/opus.so）。
set(SEMS_OPUS_INCLUDE_DIR "" CACHE PATH "sems-opus include dir (contains sems/amci/amci.h)")
set(SEMS_OPUS_PLUGIN "" CACHE FILEPATH "Path to the opus plug-in dynamic module")
if(NOT SEMS_OPUS_INCLUDE_DIR)
  message(FATAL_ERROR "SEMS_OPUS_INCLUDE_DIR not set: pass the sems-opus package include dir")
endif()

add_executable(test_sems-opus test.c sems_host_stubs.c)
# SEMS 插件加载模型：宿主（sems 主程序）以 -rdynamic 导出日志符号供
# dlopen 插件重定位，测试宿主同样需要导出
target_link_options(test_sems-opus PRIVATE -rdynamic)
target_include_directories(test_sems-opus PRIVATE "${SEMS_OPUS_INCLUDE_DIR}")
target_link_libraries(test_sems-opus ${CMAKE_DL_LIBS})

enable_testing()
add_test(NAME test_sems-opus COMMAND test_sems-opus)
if(SEMS_OPUS_PLUGIN)
  set_tests_properties(test_sems-opus PROPERTIES
                       ENVIRONMENT "SEMS_OPUS_PLUGIN=${SEMS_OPUS_PLUGIN}")
else()
  message(STATUS "SEMS_OPUS_PLUGIN not set: ctest invocation needs "
                 "SEMS_OPUS_PLUGIN pointing at lib/sems/plug-in/opus.so")
endif()
