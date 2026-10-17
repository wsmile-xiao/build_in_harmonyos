cmake_minimum_required(VERSION 3.15)
project(test_genht C)

# Find the package via Conan-generated CMakeDeps
find_package(genht REQUIRED)

# API 断言用例（单元级）：htsi/htss API 面 + hash 工具 + version 宏
add_executable(test_genht test.c)
target_link_libraries(test_genht genht::genht)

# 鸿蒙特有测试：完整端到端消费者用例 ——
# 构造输入（内嵌日志语料）→ 真实执行（htsi/htss/htpp/htip/siphash24 索引流水线
# + 扩容负载 + 资源下线）→ 产出确定性报告 → 与参考输出逐字节校验
add_executable(test_consumer test_consumer.c)
target_link_libraries(test_consumer genht::genht)

enable_testing()
add_test(NAME test_genht COMMAND test_genht)
add_test(NAME test_consumer COMMAND test_consumer)
