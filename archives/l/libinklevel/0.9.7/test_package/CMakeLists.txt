cmake_minimum_required(VERSION 3.15)
project(PackageTest C)

find_package(libinklevel CONFIG REQUIRED)

add_executable(test_package test.c)
target_link_libraries(test_package libinklevel::libinklevel)

# 鸿蒙 PC 平台特有测试：SONAME 解析 / 探测时延契约 / UTF-8 设备名 / ELF 目标
add_executable(test_ohos test_ohos.c)
target_link_libraries(test_ohos libinklevel::libinklevel)
