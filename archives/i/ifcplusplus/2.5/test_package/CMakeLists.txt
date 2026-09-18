cmake_minimum_required(VERSION 3.15)
project(test_ifcplusplus CXX)

# Find the package via Conan-generated CMakeDeps
find_package(ifcplusplus REQUIRED)

# 消费者用例：ReaderSTEP 解析 IFC4 STEP 模型 + WriterSTEP 回写校验
add_executable(test_ifcplusplus src/test.cpp)
target_link_libraries(test_ifcplusplus ifcplusplus::ifcplusplus)
target_compile_features(test_ifcplusplus PRIVATE cxx_std_17)

# 鸿蒙专项测试：GUID mask 平台路径（OHOS/ARM char 无符号）往返一致性
add_executable(test_ifcplusplus_ohos src/test_ohos.cpp)
target_link_libraries(test_ifcplusplus_ohos ifcplusplus::ifcplusplus)
target_compile_features(test_ifcplusplus_ohos PRIVATE cxx_std_17)

enable_testing()
add_test(NAME test_ifcplusplus COMMAND test_ifcplusplus)
add_test(NAME test_ifcplusplus_ohos COMMAND test_ifcplusplus_ohos)