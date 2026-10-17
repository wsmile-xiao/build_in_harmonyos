cmake_minimum_required(VERSION 3.15)
project(test_hydra C)

# hydra 为纯命令行工具（application，无共享库），test.c 作为独立
# 消费者程序编译运行（验证环境 + 基础断言）
add_executable(test_hydra test.c)

enable_testing()
add_test(NAME test_hydra COMMAND test_hydra)
