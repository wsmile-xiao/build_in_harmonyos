cmake_minimum_required(VERSION 3.15)
project(test_hippomocks CXX)

enable_testing()

find_package(hippomocks CONFIG REQUIRED)

add_executable(test_hippomocks test.cpp)
target_link_libraries(test_hippomocks PRIVATE hippomocks::hippomocks)
target_compile_features(test_hippomocks PRIVATE cxx_std_11)

# HarmonyOS 专项测试 (独立于消费者用例计数)
add_executable(test_hippomocks_ohos test_ohos.cpp)
target_link_libraries(test_hippomocks_ohos PRIVATE hippomocks::hippomocks)
target_compile_features(test_hippomocks_ohos PRIVATE cxx_std_11)

add_test(NAME test_hippomocks COMMAND test_hippomocks)
add_test(NAME test_hippomocks_ohos COMMAND test_hippomocks_ohos)