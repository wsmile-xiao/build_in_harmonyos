cmake_minimum_required(VERSION 3.15)
project(test_rcon C)

# 纯可执行包：不 find_package（无可链接目标），通过 conanrun PATH 调用 rcon。
# test.c = 冒烟(--help) + 端到端消费者用例（鸿蒙特有测试，真实 socket 往返）
add_executable(test_rcon test.c)
