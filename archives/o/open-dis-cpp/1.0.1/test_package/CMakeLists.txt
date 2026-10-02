cmake_minimum_required(VERSION 3.15)
project(test_open-dis-cpp CXX)

set(CMAKE_CXX_STANDARD 11)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# 经 Conan CMakeDeps 找到本包（package_info 的两个 component）
find_package(open-dis-cpp REQUIRED)

# 1) DIS6 协议库消费者：DataStream + EntityStatePdu 序列化回环
add_executable(test_dis6_roundtrip test_dis6_roundtrip.cpp)
target_link_libraries(test_dis6_roundtrip PRIVATE open-dis-cpp::dis6)

# 2) DIS7 协议库消费者：DIS7 独立的 DataStream + EntityStatePdu 回环
add_executable(test_dis7_roundtrip test_dis7_roundtrip.cpp)
target_link_libraries(test_dis7_roundtrip PRIVATE open-dis-cpp::dis7)

# 3) 鸿蒙平台运行时消费者：位宽/字节序/网络序落盘 + 打包 .so 动态加载核对
add_executable(test_ohos_runtime test_ohos_runtime.cpp)
target_link_libraries(test_ohos_runtime PRIVATE open-dis-cpp::dis6)

enable_testing()
add_test(NAME test_dis6_roundtrip COMMAND test_dis6_roundtrip)
add_test(NAME test_dis7_roundtrip COMMAND test_dis7_roundtrip)
add_test(NAME test_ohos_runtime COMMAND test_ohos_runtime)
