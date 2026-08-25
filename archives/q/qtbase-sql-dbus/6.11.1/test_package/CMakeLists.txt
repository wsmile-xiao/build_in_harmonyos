cmake_minimum_required(VERSION 3.15)
project(test_qtbase_sql_dbus CXX)

# 变体核心卖点：Sql（QSQLITE 驱动）+ DBus（QtDBus，QT_NO_DBUS 宏污染修复后）
find_package(Qt6 REQUIRED COMPONENTS Sql DBus)

add_executable(test_sql_dbus test.cpp)
target_link_libraries(test_sql_dbus Qt6::Sql Qt6::DBus)

enable_testing()
add_test(NAME test_sql_dbus COMMAND test_sql_dbus)
