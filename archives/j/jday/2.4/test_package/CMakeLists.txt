cmake_minimum_required(VERSION 3.15)
project(test_jday C)

find_package(jday CONFIG REQUIRED)

add_executable(test_jday test.c)
target_link_libraries(test_jday PRIVATE jday::jday)

# 静态链接测试程序，使 conan create 的 test 阶段在两种构建机上都能真实执行：
# x86_64 交叉构建机经 qemu-aarch64 binfmt 运行 aarch64 产物时，动态可执行文件会
# 因缺少 /lib/ld-musl-aarch64.so.1 而无法启动；原生 aarch64 构建机上静态链接同样可执行。
# jday 只依赖 libc，静态链接没有额外代价。
target_link_options(test_jday PRIVATE -static)

enable_testing()
add_test(NAME test_jday COMMAND test_jday)
