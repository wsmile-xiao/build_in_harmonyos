cmake_minimum_required(VERSION 3.15)
project(atari800_test LANGUAGES C)

find_package(atari800 CONFIG REQUIRED)
add_executable(atari800_test test.c)
target_link_libraries(atari800_test PRIVATE atari800::atari800)

# 上游自包含 C 测试程序 (libatari800_test): 源码原样复制自上游
# src/libatari800/libatari800_test.c, 仅使用 libatari800.h 公开 API,
# 链接安装后的 libatari800.a (见 MANIFEST.yml 审计)。
# 上游测试从主配方 build() 移入 test_package: 主配方 RREV 不变时真机
# --build=missing 命中缓存跳过 build(), 原先只在 build() 输出的
# HMBS_UPSTREAM_TEST_RESULT 从未出现 → evidence 失败; test_package
# test() 每次 conan create 必跑, 故上游测试改在这里编译 + 执行 + 输出标记。
add_executable(libatari800_test libatari800_test.c)
target_link_libraries(libatari800_test PRIVATE atari800::atari800)
