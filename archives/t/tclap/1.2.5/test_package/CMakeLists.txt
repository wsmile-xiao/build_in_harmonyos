cmake_minimum_required(VERSION 3.15)
project(test_tclap CXX)

# 消费者视角：通过 Conan 生成的 CMakeDeps 找到 tclap 包（header-only）
find_package(tclap REQUIRED CONFIG)

add_executable(test_tclap test_tclap.cpp)
target_link_libraries(test_tclap PRIVATE tclap::tclap)

# 与上游 CMakeLists 的 CMAKE_CXX_STANDARD=98 同族（本用例只需 C++11 特性）
set_target_properties(test_tclap PROPERTIES
    CXX_STANDARD 11
    CXX_STANDARD_REQUIRED ON
    CXX_EXTENSIONS OFF)

# OHOS：静态链接 C++ 运行时，测试二进制在无 LD_LIBRARY_PATH（conanrun 不含
# SDK libc++_shared.so 搜索路径）的环境下可直接运行（crcpp 先例）
target_link_options(test_tclap PRIVATE -static-libstdc++)
