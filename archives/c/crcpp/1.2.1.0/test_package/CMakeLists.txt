cmake_minimum_required(VERSION 3.15)
project(test_crcpp CXX)

# 消费者视角：通过 Conan 生成的 CMakeDeps 找到 crcpp 包
find_package(crcpp REQUIRED CONFIG)

add_executable(test_crcpp test_crcpp.cpp)
target_link_libraries(test_crcpp PRIVATE crcpp::crcpp)

# 上游 README 推荐 C++11（constexpr 路径），与上游 CMake 默认 CXX_STANDARD 一致
set_target_properties(test_crcpp PROPERTIES
    CXX_STANDARD 11
    CXX_STANDARD_REQUIRED ON
    CXX_EXTENSIONS OFF)

# 与上游 gcc Makefile 默认一致：打开小众 CRC 定义区（CRC-5/USB、CRC-64 等）
target_compile_definitions(test_crcpp PRIVATE CRCPP_INCLUDE_ESOTERIC_CRC_DEFINITIONS)

# OHOS：静态链接 C++ 运行时，测试二进制在无 LD_LIBRARY_PATH（conanrun 不含
# SDK libc++_shared.so 搜索路径）的环境下可直接运行
target_link_options(test_crcpp PRIVATE -static-libstdc++)

enable_testing()
add_test(NAME crcpp_consumer COMMAND test_crcpp)
