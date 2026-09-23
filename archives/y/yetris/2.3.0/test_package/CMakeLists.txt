cmake_minimum_required(VERSION 3.15)
project(yetris_consumer_test C)

# yetris 是 application（ncurses TUI 游戏），消费者测试以"二进制使用者"身份
# 运行打包产物并断言行为；测试程序本身不链接被测库。
add_executable(test_yetris test_yetris.c)
