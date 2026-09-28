cmake_minimum_required(VERSION 3.15)
project(test_ausweisapp C)

# 注意：故意不 find_package(ausweisapp)！
# AusweisApp 是 Qt6 GUI 应用（package_type = "application"），不导出
# CMake targets；且其 Qt 依赖（qtbase/qtwebsockets 等）均为
# cmake_find_mode=none，CMakeDeps 生成的 ausweisapp-config.cmake 会对每个
# 传递依赖调用 find_dependency()，导致 qtwebsockets 等解析失败
# （CI #59589 失败根因）。故 test.c 经 AUSWEISAPP_BIN 宏直接定位并真实
# 执行打包产物，编译的宿主程序本身只做进程调用与输出校验。

# 编译宿主测试程序：内部 popen 执行 AusweisApp --version 并验证输出。
add_executable(test_ausweisapp test.c)
target_compile_definitions(test_ausweisapp PRIVATE
    AUSWEISAPP_BIN="${AUSWEISAPP_BIN}")

enable_testing()
add_test(NAME test_ausweisapp_help COMMAND test_ausweisapp)
set_tests_properties(test_ausweisapp_help PROPERTIES
                     TIMEOUT 60)
