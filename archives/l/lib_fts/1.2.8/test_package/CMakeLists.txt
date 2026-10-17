cmake_minimum_required(VERSION 3.15)
project(test_lib_fts CXX)

# Find the package via Conan-generated CMakeDeps
find_package(lib_fts REQUIRED)

# 消费者测试：仅用公开头文件 + 公开 API
add_executable(test_lib_fts test.cpp)
target_link_libraries(test_lib_fts lib_fts::lib_fts)

# HarmonyOS 专项测试：同样仅用公开 API，额外覆盖 OHOS 使用场景
add_executable(test_lib_fts_ohos test_ohos.cpp)
target_link_libraries(test_lib_fts_ohos lib_fts::lib_fts)

# 完整端到端消费者用例（rule12）：模拟"设置项模糊搜索器"业务组件，
# 仅用公开头文件 fts_fuzzy_match.h 与公开 API 驱动 查询->匹配->排序->打开 流程
add_executable(test_lib_fts_e2e consumer_e2e.cpp)
target_link_libraries(test_lib_fts_e2e lib_fts::lib_fts)

enable_testing()
add_test(NAME test_lib_fts COMMAND test_lib_fts)
add_test(NAME test_lib_fts_ohos COMMAND test_lib_fts_ohos)
add_test(NAME test_lib_fts_e2e COMMAND test_lib_fts_e2e wlan)