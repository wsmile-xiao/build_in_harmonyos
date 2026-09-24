cmake_minimum_required(VERSION 3.15)
project(test_coinmp LANGUAGES CXX)

find_package(coinmp CONFIG REQUIRED)

# 消费者测试：加载上游 CoinTest LP 实例并通过 CoinMP C-API 求解，
# 断言求解成功、解状态最优、目标值匹配（R34：实质调用被测包 API）。
add_executable(test_coinmp test.cpp)
target_link_libraries(test_coinmp PRIVATE coinmp::coinmp)

enable_testing()
add_test(NAME coinmp_consumer COMMAND test_coinmp)
