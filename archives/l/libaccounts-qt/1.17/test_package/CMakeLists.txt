cmake_minimum_required(VERSION 3.15)
project(test_libaccounts_qt CXX)

# qtbase on ohpcd ships Qt's own Qt6Config.cmake (cmake_find_mode=none), so
# Qt6 must be found explicitly first: the AccountsQt6 interface links Qt6::Core
# (and the library itself needs Qt6::Xml). Qt6_DIR comes from the toolchain.
find_package(Qt6 COMPONENTS Core Xml CONFIG REQUIRED)
find_package(AccountsQt6 REQUIRED)

add_executable(test_libaccounts_qt test_libaccounts_qt.cpp)

target_link_libraries(test_libaccounts_qt
    AccountsQt6::AccountsQt6
    Qt6::Xml
)

enable_testing()
add_test(NAME test_libaccounts_qt COMMAND test_libaccounts_qt)
