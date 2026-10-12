cmake_minimum_required(VERSION 3.15)
project(test_networkmanager_qt CXX)

# KF6NetworkManagerQtConfig.cmake does
#   find_dependency(Qt6Core/Qt6DBus/Qt6Network) + pkg_search_module(libnm, gio-2.0)
# so the Qt6 config must be reachable *before* KF6NetworkManagerQt is looked up.
find_package(Qt6 REQUIRED COMPONENTS Core DBus Network)
find_package(KF6NetworkManagerQt REQUIRED)

add_executable(test_networkmanager_qt test.cpp)
# The upstream export defines the imported target KF6::NetworkManagerQt
# (install(EXPORT KF6NetworkManagerQtTargets ... NAMESPACE KF6::)).
target_link_libraries(test_networkmanager_qt KF6::NetworkManagerQt)

enable_testing()
add_test(NAME test_networkmanager_qt COMMAND test_networkmanager_qt)
