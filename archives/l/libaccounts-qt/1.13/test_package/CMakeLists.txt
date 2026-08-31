cmake_minimum_required(VERSION 3.15)
project(test_libaccounts_qt CXX)

set(CMAKE_AUTOMOC ON)

# Find the package via Conan-generated CMakeDeps
find_package(AccountsQt5 REQUIRED)
find_package(Qt5 COMPONENTS Core Xml REQUIRED)

add_executable(test_libaccounts_qt test_libaccounts_qt.cpp)

target_link_libraries(test_libaccounts_qt
    AccountsQt5::AccountsQt5
    Qt5::Core
    Qt5::Xml
)

enable_testing()
add_test(NAME test_libaccounts_qt COMMAND test_libaccounts_qt)
