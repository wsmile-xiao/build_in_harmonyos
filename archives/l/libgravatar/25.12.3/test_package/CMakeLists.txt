cmake_minimum_required(VERSION 3.21)
project(test_libgravatar LANGUAGES CXX)

find_package(Qt6 REQUIRED COMPONENTS Core Gui Network Widgets)
find_package(KF6Config REQUIRED CONFIG)
find_package(KF6ConfigWidgets REQUIRED CONFIG)
find_package(KF6I18n REQUIRED CONFIG)
find_package(KF6WidgetsAddons REQUIRED CONFIG)
find_package(KPim6Gravatar REQUIRED CONFIG)

enable_testing()

add_executable(test_gravatar test_gravatar.cpp)
target_compile_features(test_gravatar PRIVATE cxx_std_17)
target_link_libraries(test_gravatar PRIVATE Qt6::Core Qt6::Gui KPim6::Gravatar)
add_test(NAME test_gravatar COMMAND $<TARGET_FILE:test_gravatar>)

add_executable(test_harmonyos_cache test_harmonyos_cache.cpp)
target_compile_features(test_harmonyos_cache PRIVATE cxx_std_17)
target_link_libraries(test_harmonyos_cache PRIVATE Qt6::Core Qt6::Gui KPim6::Gravatar)
add_test(NAME test_harmonyos_cache COMMAND $<TARGET_FILE:test_harmonyos_cache>)
