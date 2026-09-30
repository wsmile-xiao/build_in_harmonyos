cmake_minimum_required(VERSION 3.15)
project(test_ifcplusplus CXX)

# 通过 Conan 生成的 CMakeDeps 查找已安装的 ifcplusplus 包
find_package(ifcplusplus REQUIRED)

# 消费者用例：ReaderSTEP 解析 IFC4 STEP 模型 -> 遍历实体 -> WriterSTEP 回写校验
add_executable(test_ifcplusplus src/test.cpp)
target_link_libraries(test_ifcplusplus ifcplusplus::ifcplusplus)
target_compile_features(test_ifcplusplus PRIVATE cxx_std_17)

# 鸿蒙专项用例：真实消费者端到端流程（解析 -> 几何体构建 -> 回写 -> 重解析）
# 覆盖 Carve 几何内核（本次适配的 carve 静态化 + C++17 兼容路径）
add_executable(test_ifcplusplus_ohos src/test_ohos.cpp)
target_link_libraries(test_ifcplusplus_ohos ifcplusplus::ifcplusplus)
target_compile_features(test_ifcplusplus_ohos PRIVATE cxx_std_17)

enable_testing()
add_test(NAME test_ifcplusplus COMMAND test_ifcplusplus)
add_test(NAME test_ifcplusplus_ohos COMMAND test_ifcplusplus_ohos)
