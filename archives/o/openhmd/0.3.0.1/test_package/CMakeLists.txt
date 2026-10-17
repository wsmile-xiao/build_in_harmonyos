cmake_minimum_required(VERSION 3.15)
project(openhmd_consumer_tests C)

# 消费者测试：只使用上游公共头文件 <openhmd.h>，链接 conan 生成的导入目标
find_package(openhmd REQUIRED)
find_package(hidapi REQUIRED)

add_executable(openhmd_consumer_tests test.c)
target_link_libraries(openhmd_consumer_tests PRIVATE
    openhmd::openhmd
    hidapi::hidapi
    m
)
