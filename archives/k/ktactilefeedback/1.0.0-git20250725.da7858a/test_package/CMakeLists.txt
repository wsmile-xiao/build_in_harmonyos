cmake_minimum_required(VERSION 3.15)
project(test_ktactilefeedback CXX)

# KTactileFeedback installs its own config in lib/cmake/KTactileFeedback
# (cmake_find_mode=none), so find the package the same way a downstream
# consumer would: find_package(KTactileFeedback).
find_package(KTactileFeedback REQUIRED)
find_package(Qt6 REQUIRED COMPONENTS Core Qml)

add_executable(test_ktactilefeedback test.cpp)
target_link_libraries(test_ktactilefeedback PRIVATE KTactileFeedback::KTactileFeedback)
# The upstream package exports its forwarding headers (QFeedbackActuator,
# QFeedbackEffect, ...) into include/KTactileFeedback but does not attach an
# INTERFACE_INCLUDE_DIRECTORIES to the exported target (KDE consumers derive
# it from TactileFeedback_INSTALL_PREFIX). Mirror that convention so
# #include "QFeedbackActuator" resolves.
target_include_directories(test_ktactilefeedback PRIVATE
    "${TactileFeedback_INSTALL_PREFIX}/include/KTactileFeedback")
# The public API headers include QtCore/QObject etc.; the complete consumer
# test also drives the org.kde.tactilefeedback QML module through the QML
# engine (Qt6::Qml), mirroring the KDE declarative consumer flow.
target_link_libraries(test_ktactilefeedback PRIVATE Qt6::Core Qt6::Qml)

enable_testing()
add_test(NAME test_ktactilefeedback COMMAND test_ktactilefeedback)