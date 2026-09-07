cmake_minimum_required(VERSION 3.16)
project(test_libkdepim LANGUAGES CXX)

find_package(Qt6 REQUIRED COMPONENTS Core DBus Gui Widgets)
find_package(KF6Codecs REQUIRED CONFIG)
find_package(KF6Config REQUIRED CONFIG)
find_package(KF6WidgetsAddons REQUIRED CONFIG)
find_package(KF6Completion REQUIRED CONFIG)
find_package(KF6I18n REQUIRED CONFIG)
find_package(KPim6Libkdepim REQUIRED CONFIG)

add_executable(test_libkdepim test_libkdepim.cpp)
target_compile_features(test_libkdepim PRIVATE cxx_std_17)
target_link_options(test_libkdepim PRIVATE "-Wl,--as-needed")
target_link_libraries(test_libkdepim PRIVATE Qt6::Core KPim6::Libkdepim)

enable_testing()
add_test(NAME test_libkdepim COMMAND $<TARGET_FILE:test_libkdepim>)
