cmake_minimum_required(VERSION 3.15)
project(test_jwt-cpp CXX)

# Find the package via Conan-generated CMakeDeps
find_package(jwt-cpp REQUIRED)

# L1 消费者 smoke test
add_executable(test_jwt-cpp test_package.cpp)
target_link_libraries(test_jwt-cpp jwt-cpp::jwt-cpp)

# HarmonyOS 专项适配测试（HS256/RS256/ES256 + 过期校验）
add_executable(ohos_adapt_test ohos_adapt_test.cpp)
target_link_libraries(ohos_adapt_test jwt-cpp::jwt-cpp)

enable_testing()
add_test(NAME test_jwt-cpp COMMAND test_jwt-cpp)
add_test(NAME ohos_adapt_test COMMAND ohos_adapt_test)