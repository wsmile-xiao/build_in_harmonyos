cmake_minimum_required(VERSION 3.15)
project(test_shadowsocks_e2e C)

# 本测试把被 Conan 打包的真实可执行文件当黑盒驱动，不需要链接被测库头文件；
# find_package 仍然调用，以确保 test_package 的依赖图确实解析到被测包。
find_package(shadowsocks-libev CONFIG REQUIRED)

add_executable(test_shadowsocks_e2e test_shadowsocks_e2e.c)
