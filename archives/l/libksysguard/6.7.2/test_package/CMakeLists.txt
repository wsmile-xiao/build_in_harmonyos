cmake_minimum_required(VERSION 3.20)
project(test_libksysguard LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(Qt6 REQUIRED COMPONENTS Core Gui)
# The published qtbase and qtdeclarative packages split the Qt6 umbrella
# across two prefixes, and Qt6Config.cmake only accepts component configs
# located under its own prefix, so find_package(Qt6 ... Qml) cannot resolve
# the Qml component. qtdeclarative ships its own Qt6QmlConfig.cmake, so
# resolve it directly: KSysGuard::Formatter's imported target links
# Qt6::Qml (its Unit.h even includes qqmlregistration.h).
find_package(Qt6Qml REQUIRED CONFIG)
# Upstream package config (lib/cmake/KSysGuard/KSysGuardConfig.cmake):
# resolves Qt6Core/Network/Widgets and KF6Config/KF6I18n dependencies and
# imports the KSysGuard::Formatter/ProcessCore/Sensors/SensorFaces/SystemStats
# targets from the conan package folder.
find_package(KSysGuard REQUIRED CONFIG)

add_executable(test_libksysguard test_libksysguard.cpp)
target_link_libraries(test_libksysguard PRIVATE
    Qt6::Core
    KSysGuard::Formatter
)

enable_testing()
add_test(NAME test_libksysguard COMMAND test_libksysguard)
