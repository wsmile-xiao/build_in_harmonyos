cmake_minimum_required(VERSION 3.15)
project(test_remctl_package C)

find_package(remctl REQUIRED)   # conan CMakeDeps 以 cpp_info.set_property pkg_config_name 之外的 cmake 目标名生成；真机核

add_executable(test_remctl test_remctl.c)
target_link_libraries(test_remctl PRIVATE remctl::remctl)
