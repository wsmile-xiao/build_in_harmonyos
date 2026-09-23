cmake_minimum_required(VERSION 3.15)
project(test_ssdeep C)

# Find the package via Conan-generated CMakeDeps
find_package(ssdeep REQUIRED)

# 消费者测试：调用公开 API fuzzy_hash_buf/fuzzy_compare（test.c）
add_executable(test_ssdeep test.c)
target_link_libraries(test_ssdeep ssdeep::ssdeep)

# HarmonyOS 专项测试：9 项断言（确定性/文件哈希/相似度 100-99-0/CLI 管线）
# 源文件随本 PR 交付（ssdeep-ohos-test.c）；argv[1] 注入被测包 CLI 路径
# （test_package/conanfile.py 通过 SSDEEP_CLI 变量传入）。
# 非 OHOS 平台仍编译运行库 API 断言部分（CLI 依赖被测包 bin/ssdeep，
# 由 conanfile.py 在 can_run 时传入）。
add_executable(test_ssdeep_ohos ssdeep-ohos-test.c)
target_link_libraries(test_ssdeep_ohos ssdeep::ssdeep)
if(DEFINED SSDEEP_CLI AND NOT SSDEEP_CLI STREQUAL "")
    add_test(NAME test_ssdeep_ohos COMMAND test_ssdeep_ohos "${SSDEEP_CLI}")
else()
    add_test(NAME test_ssdeep_ohos COMMAND test_ssdeep_ohos)
endif()

enable_testing()
add_test(NAME test_ssdeep COMMAND test_ssdeep)
