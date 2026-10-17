cmake_minimum_required(VERSION 3.15)
project(test_ki18n CXX)

find_package(Qt6 REQUIRED COMPONENTS Core Qml)
find_package(KF6I18n REQUIRED Qml)

add_executable(test_ki18n test.cpp)
target_link_libraries(test_ki18n PRIVATE KF6::I18n KF6::I18nQml Qt6::Qml)

enable_testing()
add_test(NAME test_ki18n COMMAND test_ki18n)
