cmake_minimum_required(VERSION 3.15)
project(test_kexec_tools C)

# kexec-tools 是纯命令行工具包（无链接库）：消费者测试通过执行包内
# 二进制验证（工具构建可用性口径），不链接 kexec::kexec-tools 目标。
add_executable(test_kexec_tools test.c)

enable_testing()
# 运行时由 conanrunenv 注入包 bin 目录（VirtualRunEnv 生成）；
# 回退参数缺省时 test.c 内部回退 PATH/默认布局。
add_test(NAME test_kexec_tools COMMAND test_kexec_tools $ENV{CONAN_RUNENV_KEXEC_TOOLS})
