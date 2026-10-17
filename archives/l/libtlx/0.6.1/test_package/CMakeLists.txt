cmake_minimum_required(VERSION 3.15)
project(test_libtlx CXX)

set(CMAKE_CXX_STANDARD 14)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# 只通过 Conan 生成的 CMakeDeps 配置找包（不碰上游源码树）
find_package(tlx REQUIRED CONFIG)

if(NOT TARGET tlx::tlx)
  message(FATAL_ERROR "tlx::tlx target missing: cpp_info.cmake_target_name 未对齐上游 install(EXPORT tlx-targets)")
endif()

add_executable(consumer consumer.cpp)
target_link_libraries(consumer PRIVATE tlx::tlx)

add_executable(ohos_special_test ohos_special_test.cpp)
target_link_libraries(ohos_special_test PRIVATE tlx::tlx)

# 静态 libc++：消费者二进制免 LD_LIBRARY_PATH 直跑（OHOS 设备动态
# libc++_shared.so 默认搜索路径不含 ohos-sdk 运行库目录；本机已实测
# -static-libstdc++ 链接运行 exit 0）
target_link_options(consumer PRIVATE -static-libstdc++)
target_link_options(ohos_special_test PRIVATE -static-libstdc++)
