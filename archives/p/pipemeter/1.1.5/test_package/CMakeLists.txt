cmake_minimum_required(VERSION 3.15)
project(pipemeter_test_package C)

set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)

# pipemeter 是 package_type=application 的包：它只交付 bin/pipemeter 可执行文件，
# 不导出库、不导出 CMake config package，所以这里刻意不写 find_package /
# target_link_libraries（写了会直接找不到目标）。被测对象通过 test() 里
# 以管道方式真实执行来验证（见 smoke.sh 与 conanfile.py 的 test()）。
#
# pump.c 是测试侧的数据生产者：编译出的 pump 精确产出 N 字节已知模式数据，
# 由 smoke.sh 灌进包内 pipemeter，断言其字节计量列与 stdout 透传字节数。
add_executable(pump pump.c)
target_compile_options(pump PRIVATE -Wall -Wextra)
