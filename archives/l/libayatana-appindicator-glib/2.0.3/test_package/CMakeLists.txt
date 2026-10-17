cmake_minimum_required(VERSION 3.15)
project(test_package C)

# Find the package via Conan-generated CMakeDeps
find_package(libayatana-appindicator-glib REQUIRED)

# 1) 鸿蒙特有端到端消费者用例：驱动事件循环验证 app_indicator_* 全流程
#    （rule12：完整消费者用例，非纯断言）
add_executable(test_package test_package.c)
target_link_libraries(test_package PRIVATE libayatana-appindicator-glib::libayatana-appindicator-glib)

# 2) 上游单元测试 test-libappindicator.c（2.0.3 tag 逐字复制、未修改）：
#    纯 g_test 进程内用例（6 个），不依赖 dbus-test-runner/Xvfb，真实执行
#    （rule4：真实执行上游测试用例）
add_executable(test-libappindicator test-libappindicator.c)
# 上游源码以 <ayatana-appindicator.h> 引用头文件，补包内
# include/libayatana-appindicator-glib 搜索路径（不改动上游源码）
get_target_property(_AI_INCLUDE_DIRS libayatana-appindicator-glib::libayatana-appindicator-glib INTERFACE_INCLUDE_DIRECTORIES)
foreach(_inc ${_AI_INCLUDE_DIRS})
    target_include_directories(test-libappindicator PRIVATE "${_inc}/libayatana-appindicator-glib")
endforeach()
target_link_libraries(test-libappindicator PRIVATE libayatana-appindicator-glib::libayatana-appindicator-glib)
