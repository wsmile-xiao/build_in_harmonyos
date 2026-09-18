cmake_minimum_required(VERSION 3.15)
project(test_package C)

# libosmocore 通过公共头文件导出线程局部变量（osmo_ctx / osmo_cbsp_errstr）。
# OHOS clang 默认 -femulated-tls；配方已通过 cpp_info.cflags 传播 -fno-emulated-tls，
# 这里显式兜底，确保库与测试使用同一 TLS 模型（TLS 模型不一致会在运行时段错误）。
set(CMAKE_C_FLAGS "${CMAKE_C_FLAGS} -fno-emulated-tls")

find_package(libosmocore CONFIG REQUIRED)
find_package(Threads REQUIRED)

# 冒烟测试：跨 libosmocore / libosmogsm / libosmocodec 调用真实 API
add_executable(test_smoke test.c)
target_link_libraries(test_smoke PRIVATE
    libosmocore::osmocore
    libosmocore::osmogsm
    libosmocore::osmocodec)

# 鸿蒙特有测试：跨 DSO 线程局部变量（TLS）一致性
add_executable(test_ohos_tls test_ohos_tls.c)
target_link_libraries(test_ohos_tls PRIVATE
    libosmocore::osmocore
    libosmocore::osmogsm
    Threads::Threads)
