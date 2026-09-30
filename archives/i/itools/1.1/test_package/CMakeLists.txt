cmake_minimum_required(VERSION 3.15)
project(itools_smoke C)

# itools 是 application 包，没有可链接的库；消费者测试以调用者身份
# 运行安装后的 ical/idate/ipraytime 并对退出码与输出结构断言。
# 被测二进制目录由配方通过 ITOOLS_BIN 传入绝对路径。
if(NOT DEFINED ITOOLS_BIN)
    message(FATAL_ERROR "ITOOLS_BIN must be set by the conanfile generate()")
endif()

# 路径在这里就定型成 C 字符串字面量，避免裸 token 进宏体（含空格即断）。
add_compile_definitions(ITOOLS_BIN="${ITOOLS_BIN}")

add_executable(itools_smoke smoke.c)

enable_testing()
add_test(NAME itools_smoke COMMAND itools_smoke)
