cmake_minimum_required(VERSION 3.15)
project(mbw_test C)

# mbw 可执行文件由 conan 安装，运行期通过 VirtualRunEnv 注入 PATH。
# 不要在构建期 find_program（build 阶段 PATH 里还没有 mbw 的 bin 目录），
# test.c 直接用 "mbw" 由 shell 按 PATH 查找。
add_executable(mbw_test test.c)
