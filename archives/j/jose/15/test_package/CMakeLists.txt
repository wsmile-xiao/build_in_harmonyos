cmake_minimum_required(VERSION 3.15)
project(test_jose C)

# Find the package via Conan-generated CMakeDeps
find_package(jose REQUIRED)

add_executable(test_jose test.c)
target_link_libraries(test_jose jose::jose)

# HarmonyOS 专项测试：JWS 签名/验证/JWK 指纹等集成断言（jose_ohos_test.c）
add_executable(test_jose_ohos jose_ohos_test.c)
target_link_libraries(test_jose_ohos jose::jose)

enable_testing()
add_test(NAME test_jose COMMAND test_jose)
add_test(NAME test_jose_ohos COMMAND test_jose_ohos)
