cmake_minimum_required(VERSION 3.15)
project(unittestpp_test_package LANGUAGES CXX)

# Conan CMakeDeps 生成的 Config（cmake_file_name = "UnitTest++"，
# 目标名与上游安装树一致：无命名空间 UnitTest++）
find_package(UnitTest++ REQUIRED)

# 正向消费者用例（9 个）
add_executable(test_unittestpp test_unittestpp.cpp)
target_link_libraries(test_unittestpp PRIVATE UnitTest++)

# 反向对照（预期失败：断言失败 + raise(SIGSEGV) 信号翻译必须被如实上报）
add_executable(test_unittestpp_negative test_unittestpp_negative.cpp)
target_link_libraries(test_unittestpp_negative PRIVATE UnitTest++)
