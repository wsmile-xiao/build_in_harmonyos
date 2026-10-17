cmake_minimum_required(VERSION 3.20)
project(wmload_test_package C)

set(CMAKE_C_STANDARD 99)
set(CMAKE_C_EXTENSIONS ON)

add_executable(ohos_procfs_probe ohos_procfs_probe.c)
target_compile_options(ohos_procfs_probe PRIVATE -Wall -Wextra -Werror)
