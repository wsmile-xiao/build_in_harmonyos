cmake_minimum_required(VERSION 3.15)
project(test_dcc C)

# dcc-extras 由 conan 的 CMakeDeps 生成 find_package 配置
find_package(dcc-extras REQUIRED)

add_executable(test_dcc test_dcc.c)
target_link_libraries(test_dcc dcc-extras::dcc-extras)

enable_testing()
add_test(NAME test_dcc COMMAND test_dcc)
