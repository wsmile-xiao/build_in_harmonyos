cmake_minimum_required(VERSION 3.15)
project(test_rsgl C)

# Find the package via Conan-generated CMakeDeps
find_package(rsgl REQUIRED)

add_executable(test_rsgl test.c)
target_link_libraries(test_rsgl rsgl::rsgl)

# OHOS 图形栈：消费者测试真实创建 EGL pbuffer 上下文 + GLES3 并调用
# RSGL 公开 API 绘制（R34 实质调用，非空壳）。OHOS 适配版 clang 自带
# sysroot，直接按库名链接 EGL/GLESv3（其默认搜索路径覆盖 SDK 库目录）。
target_link_libraries(test_rsgl EGL GLESv3 m)

enable_testing()
add_test(NAME test_rsgl COMMAND test_rsgl)
