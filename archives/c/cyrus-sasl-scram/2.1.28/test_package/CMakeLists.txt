cmake_minimum_required(VERSION 3.15)
project(test_cyrus_sasl_scram C)

# 静态包：绝不允许通过 module 模式解析到系统 libsasl2.so.3。
# CONFIG 强制使用 Conan 生成的 cyrus-sasl-scram-config.cmake（指向 libsasl2.a）；
# BUILD_SHARED_LIBS OFF 让消费者保持全静态，避免在 OHOS 上留下
# DT_NEEDED libsasl2.so.3（SONAME 会解析到不兼容的 stub）。
set(BUILD_SHARED_LIBS OFF)
find_package(cyrus-sasl-scram REQUIRED CONFIG)

add_executable(test_scram test_scram.c)
target_link_libraries(test_scram PRIVATE cyrus-sasl-scram::cyrus-sasl-scram)

enable_testing()
add_test(NAME test_scram COMMAND test_scram)
