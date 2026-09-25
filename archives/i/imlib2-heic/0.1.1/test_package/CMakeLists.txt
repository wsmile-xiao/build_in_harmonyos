cmake_minimum_required(VERSION 3.15)
project(test_imlib2-heic C)

# imlib2-heic 是 dlopen 插件包：不提供链接库/头文件，消费者直接
# dlopen 安装包内 lib/imlib2/loaders/heic.so（路径由 conanfile.py 以
# 环境变量 IMLIB2_HEIC_PLUGIN 传入）。OHOS(musl) 的 dlopen 在 libc 中。

add_executable(test_imlib2-heic test.c)

enable_testing()
add_test(NAME test_imlib2-heic COMMAND test_imlib2-heic)