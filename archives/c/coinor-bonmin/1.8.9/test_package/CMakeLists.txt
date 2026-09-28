cmake_minimum_required(VERSION 3.15)
project(coinor_bonmin_test LANGUAGES CXX)

find_package(coinor-bonmin CONFIG REQUIRED)

# 消费者冒烟测试：链接 libbonmin，公开 API 跑完整 B-BB 并断言最优值（R34）
add_executable(bonmin_smoke bonmin_smoke.cpp MyTMINLP.cpp)
target_link_libraries(bonmin_smoke PRIVATE coinor-bonmin::coinor-bonmin)

# HarmonyOS 专项测试：安装头版本自报 + Ipopt 运行时初始化 + 完整求解链断言
add_executable(bonmin_ohos_test bonmin_ohos_test.cpp MyTMINLP.cpp)
target_link_libraries(bonmin_ohos_test PRIVATE coinor-bonmin::coinor-bonmin)

enable_testing()
add_test(NAME bonmin_smoke COMMAND bonmin_smoke)
add_test(NAME bonmin_ohos COMMAND bonmin_ohos_test)
