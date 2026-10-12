cmake_minimum_required(VERSION 3.16)
project(kinfocenter_consumer_test LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(Qt6 REQUIRED COMPONENTS Core)
find_package(KF6CoreAddons REQUIRED CONFIG)

# The consumer test drives the installed KCM payload (KIC_TEST_PACKAGE_DIR
# env): it loads kcm_cpu through KPluginFactory::loadFactory (the exact
# systemsettings mechanism), dlopen()s libKInfoCenterInternal.so.1 and
# verifies the installed KCM module set. Only QtCore + KF6CoreAddons are
# needed for the driving code.
add_executable(kinfocenter_consumer_test main.cpp)
target_link_libraries(kinfocenter_consumer_test PRIVATE Qt6::Core KF6::CoreAddons)

enable_testing()
add_test(NAME kinfocenter_consumer_test COMMAND kinfocenter_consumer_test)
