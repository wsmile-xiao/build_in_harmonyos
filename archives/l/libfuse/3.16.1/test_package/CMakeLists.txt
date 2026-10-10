cmake_minimum_required(VERSION 3.15)
project(test_libfuse C)

# Find the package via Conan-generated CMakeDeps
find_package(libfuse REQUIRED)

add_executable(test_libfuse test.c)
target_link_libraries(test_libfuse libfuse::libfuse)
# fuse_common.h documents that 32-bit targets need a 64-bit file offset
target_compile_definitions(test_libfuse PRIVATE _FILE_OFFSET_BITS=64)

# 鸿蒙特有端到端消费者用例：内存文件系统完整工作流
add_executable(test_fs_consumer test_fs_consumer.c)
target_link_libraries(test_fs_consumer libfuse::libfuse)
target_compile_definitions(test_fs_consumer PRIVATE _FILE_OFFSET_BITS=64)

enable_testing()
add_test(NAME test_libfuse COMMAND test_libfuse)
add_test(NAME test_fs_consumer COMMAND test_fs_consumer)
