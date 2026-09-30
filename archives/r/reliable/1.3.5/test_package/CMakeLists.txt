cmake_minimum_required(VERSION 3.15)

# 消费者用例：以"库的使用者"身份链接 reliable 的安装产物。
# 纯 C 项目（reliable 是 C 库，消费者侧无需 C++ 编译器）。
project(reliable_consumer_test C)

# Conan CMakeDeps 会按 recipe 里声明的
#   cpp_info.set_property("cmake_file_name", "reliable")
#   cpp_info.set_property("cmake_target_name", "reliable::reliable")
# 生成 reliable-config.cmake / reliable-config-version.cmake，
# 因此这里用 CONFIG 模式查找即可，无需上游提供任何 CMake 包配置。
find_package(reliable CONFIG REQUIRED)

add_executable(test_reliable test_reliable.c)

target_link_libraries(test_reliable PRIVATE reliable::reliable)

# 在 OHOS clang 下保持 -Wall 友好；本例程不使用任何平台特有 API
set_target_properties(test_reliable PROPERTIES
    C_STANDARD 99
    C_STANDARD_REQUIRED ON)
