cmake_minimum_required(VERSION 3.15)
project(test_clang20-ccache C)

# R34: clang20-ccache 是 CLI 工具包（无库 API，cpp_info.libs 为空），
# 不得把工具包伪当库链接（find_package/target_link_libraries 无效且误导）。
# 测试程序 test.c 在运行时通过 PATH 直接执行打包的 ccache 二进制并断言，
# 因此仅需编译独立可执行文件，不链接任何包内库目标。
add_executable(test_clang20-ccache test.c)

enable_testing()
add_test(NAME test_clang20-ccache COMMAND test_clang20-ccache)