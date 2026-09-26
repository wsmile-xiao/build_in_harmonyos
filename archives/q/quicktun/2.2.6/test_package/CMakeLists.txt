cmake_minimum_required(VERSION 3.15)
project(quicktun_test_package C)

# 预言机侧：独立链 libsodium，在进程内算 Curve25519 公钥来核对被测二进制的输出
find_package(libsodium REQUIRED CONFIG)

add_executable(test_quicktun test_quicktun.c)
target_link_libraries(test_quicktun PRIVATE libsodium::libsodium)

# 被测物位置由 test_package/conanfile.py 从被测试包的 bindirs 解析后传入
target_compile_definitions(test_quicktun PRIVATE
    QUICKTUN_KEYPAIR="${QUICKTUN_KEYPAIR}"
    QUICKTUN_VERSION="${QUICKTUN_VERSION}")

enable_testing()
add_test(NAME quicktun_keypair_consumer COMMAND test_quicktun)
