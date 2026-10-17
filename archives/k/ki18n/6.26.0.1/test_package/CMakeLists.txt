cmake_minimum_required(VERSION 3.16)
project(test_ki18n CXX)

find_package(KF6I18n REQUIRED)
find_package(Qt6Core REQUIRED)
find_package(Qt6Qml REQUIRED)

add_executable(test_ki18n test.cpp)
target_link_libraries(test_ki18n PRIVATE KF6::I18n KF6::I18nQml Qt6::Core Qt6::Qml)

enable_testing()
add_test(NAME test_ki18n COMMAND test_ki18n)
