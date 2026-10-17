cmake_minimum_required(VERSION 3.15)
project(test_bc-ur CXX)

# Find the package via Conan-generated CMakeDeps
find_package(bc-ur REQUIRED)

# 消费者测试：仅经公开头 <bc-ur/bc-ur.hpp> + 公开 API 使用库
add_executable(test_bc-ur test.cpp)
target_link_libraries(test_bc-ur bc-ur::bc-ur)
target_compile_features(test_bc-ur PRIVATE cxx_std_17)

# HarmonyOS 专项测试：crc32 已知向量 + Bytewords minimal 往返 +
# 256 KiB 大消息 fountain 流式解码，严格编译 (-Werror)
add_executable(test_bc-ur_ohos ohos_test.cpp)
target_link_libraries(test_bc-ur_ohos bc-ur::bc-ur)
target_compile_features(test_bc-ur_ohos PRIVATE cxx_std_17)
target_compile_options(test_bc-ur_ohos PRIVATE -Wall -Wextra -Werror)

enable_testing()
add_test(NAME test_bc-ur COMMAND test_bc-ur)
add_test(NAME test_bc-ur_ohos COMMAND test_bc-ur_ohos)