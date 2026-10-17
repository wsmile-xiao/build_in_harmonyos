cmake_minimum_required(VERSION 3.15)

# 消费者用例：以"库的使用者"身份链接 ruy 的安装产物。
# ruy 是 C++14 库，消费者侧需要 C++ 编译器。
project(ruy_consumer_test CXX)

# Conan CMakeDeps 会按 recipe 里声明的
#   cpp_info.set_property("cmake_file_name", "ruy")
#   cpp_info.set_property("cmake_target_name", "ruy::ruy")
# 生成 ruy-config.cmake / ruy-config-version.cmake，
# 因此这里用 CONFIG 模式查找即可。ruy-config.cmake 内部还会
# find_dependency(cpuinfo)（cpuinfo 是 ruy 的公开依赖），
# 对应的 cpuinfo-config.cmake 同样由 CMakeDeps 提供，无需上游提供任何
# 手写 CMake 包配置。
find_package(ruy CONFIG REQUIRED)

add_executable(test_ruy test_ruy.cpp)

target_link_libraries(test_ruy PRIVATE ruy::ruy)

set_target_properties(test_ruy PROPERTIES
    CXX_STANDARD 14
    CXX_STANDARD_REQUIRED ON)
