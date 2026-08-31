cmake_minimum_required(VERSION 3.15)
project(test_actiona C)

# test 通过 dlopen 加载 actiontools.so（test.c），不直接链接被测库：
# 链接会让 test_actiona 启动时立即加载 actiontools.so 的全部 DT_NEEDED
# （含相对路径 ../tools/tools.so，安装布局 lib/actiona/ 下无法解析），
# 导致 ctest 运行时动态链接失败。仅用 dlopen + dlsym 符号验证。
add_executable(test_actiona test.c)
target_compile_definitions(test_actiona PRIVATE ACTIONA_LIB_DIR="${ACTIONA_LIB_DIR}")
