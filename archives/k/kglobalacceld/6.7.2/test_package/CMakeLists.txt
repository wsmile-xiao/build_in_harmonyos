cmake_minimum_required(VERSION 3.16)
project(test_ohos_daemon CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(Qt6 REQUIRED COMPONENTS Core DBus)
# KGlobalAccelDConfig.cmake does not find_dependency(KF6GlobalAccel) — the
# exported K::KGlobalAccelD target links KF6::GlobalAccel (upstream assumes
# consumers resolve it themselves, as kwin does).
find_package(KF6GlobalAccel REQUIRED)
find_package(KGlobalAccelD REQUIRED)

add_executable(test_ohos_daemon test.cpp)
target_link_libraries(test_ohos_daemon K::KGlobalAccelD Qt6::DBus Qt6::Core)

enable_testing()
add_test(NAME test_ohos_daemon COMMAND test_ohos_daemon)
