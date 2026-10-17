cmake_minimum_required(VERSION 3.16)
project(boost184_contract_test_package CXX)

find_package(boost1.84-contract REQUIRED CONFIG)

add_executable(test_boost_contract test_boost_contract.cpp)
target_link_libraries(test_boost_contract PRIVATE boost1.84-contract::boost1.84-contract)

# OHOS：测试二进制静态链接 libc++ 运行时（-static-libstdc++），
# 运行时不依赖 LD_LIBRARY_PATH 指向 SDK 的 libc++_shared.so——
# conanrun 环境不含 profile buildenv 的 SDK 库路径，动态链接会导致
# "Error loading shared library libc++_shared.so" (rc=127)。
target_link_options(test_boost_contract PRIVATE -static-libstdc++)

enable_testing()
add_test(NAME boost184_contract_smoke COMMAND test_boost_contract)
