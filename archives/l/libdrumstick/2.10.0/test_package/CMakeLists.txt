cmake_minimum_required(VERSION 3.16)
project(test_libdrumstick CXX)

# 上游 drumstick-config.cmake 检查普通变量 QT_VERSION_MAJOR，
# 而 Qt6Config.cmake 仅设置目录属性，故在此显式声明。
set(QT_VERSION_MAJOR 6)

# 上游自带的 drumstick-config.cmake：find_package(drumstick COMPONENTS file rt)
find_package(Qt6 REQUIRED COMPONENTS Core)
find_package(drumstick REQUIRED COMPONENTS file rt)

add_executable(test_libdrumstick test_libdrumstick.cpp)
target_link_libraries(test_libdrumstick PRIVATE Drumstick::File)
target_link_libraries(test_libdrumstick PRIVATE Drumstick::RT)
target_link_libraries(test_libdrumstick PRIVATE Qt6::Core)

set_property(TARGET test_libdrumstick PROPERTY CXX_STANDARD 17)
set_property(TARGET test_libdrumstick PROPERTY CXX_STANDARD_REQUIRED ON)

enable_testing()
add_test(NAME test_libdrumstick COMMAND test_libdrumstick)