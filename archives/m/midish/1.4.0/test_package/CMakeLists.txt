cmake_minimum_required(VERSION 3.16)
project(test_midish CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# HarmonyOS 专项测试：平台适配核心（管道 EOF 仅 POLLHUP 时 midish 必须退出）、
# 安装产物的可重定位 ELF64 与 shell 前端、示例/文档/man page 布局。
# 该测试只用 POSIX 接口，不链接被测包（被测包是应用）。
add_executable(test_midish_ohos ohos_test.cpp)
target_compile_options(test_midish_ohos PRIVATE -Wall -Wextra -Werror)

enable_testing()
add_test(NAME test_midish_ohos COMMAND test_midish_ohos)
