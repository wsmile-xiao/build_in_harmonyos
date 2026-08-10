cmake_minimum_required(VERSION 3.5)
project(test_groonga)
find_package(groonga REQUIRED)
# test_groonga：链接 groonga 验证头文件 + API 链接可用（编译即验证）
add_executable(test_groonga test.c)
target_link_libraries(test_groonga groonga::groonga)
# elf_check：不链接 groonga（纯文件读取），校验 libgroonga.so.0 ELF magic。
# 运行 test_groonga 会动态加载 libgroonga.so.0（依赖 libc++_shared.so，
# OHOS CI 沙箱缺失，CI #16883/#16929 Error loading shared library），
# 故运行校验交给 elf_check（test() 中执行）。
add_executable(elf_check elf_check.c)
