cmake_minimum_required(VERSION 3.16)
project(test_gravatar LANGUAGES CXX)

find_package(Qt6 REQUIRED COMPONENTS Core Gui Network)
find_package(KF6Config REQUIRED CONFIG)
find_package(KF6CoreAddons REQUIRED CONFIG)
find_package(KF6I18n REQUIRED CONFIG)
find_package(KF6ConfigWidgets REQUIRED CONFIG)
find_package(KF6WidgetsAddons REQUIRED CONFIG)
find_package(KPim6Gravatar REQUIRED CONFIG)

add_executable(test_gravatar test_gravatar.cpp)
target_compile_features(test_gravatar PRIVATE cxx_std_17)
target_link_libraries(test_gravatar PRIVATE Qt6::Core Qt6::Gui Qt6::Network KPim6::Gravatar)

enable_testing()
add_test(NAME test_gravatar COMMAND $<TARGET_FILE:test_gravatar>)
