cmake_minimum_required(VERSION 3.15)
project(test_kangaru LANGUAGES CXX)

find_package(kangaru CONFIG REQUIRED)

add_executable(test_kangaru test.cpp)
target_compile_features(test_kangaru PRIVATE cxx_std_11)
target_link_libraries(test_kangaru PRIVATE kangaru::kangaru)

enable_testing()
add_test(NAME test_kangaru COMMAND test_kangaru)

# OHOS 专项可移植性测试：独立于上游与基础消费者测试的真实 API 断言。
add_executable(test_kangaru_ohos ohos_portability.cpp)
target_compile_features(test_kangaru_ohos PRIVATE cxx_std_17)
target_link_libraries(test_kangaru_ohos PRIVATE kangaru::kangaru)
add_test(NAME test_kangaru_ohos COMMAND test_kangaru_ohos)