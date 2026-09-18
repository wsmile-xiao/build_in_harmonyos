cmake_minimum_required(VERSION 3.16)
project(test_phonon CXX)

find_package(Phonon4Qt6 REQUIRED)

add_executable(test_phonon test_phonon.cpp)
target_link_libraries(test_phonon Phonon::phonon4qt6)

# HarmonyOS 专项测试（R51 鸿蒙特有测试）：验证 OHOS 适配行为
add_executable(test_ohos test_ohos.cpp)
target_link_libraries(test_ohos Phonon::phonon4qt6)

enable_testing()
add_test(NAME test_phonon COMMAND test_phonon)
add_test(NAME test_ohos COMMAND test_ohos)