cmake_minimum_required(VERSION 3.15)
project(test_dialog C)

# Simple test program that calls dialog_version() — does NOT include
# dialog.h directly (avoids transitive ncurses header dependency).
# Instead, declares the prototype and links against libdialog.a.
find_package(dialog REQUIRED)

add_executable(test_dialog test.c)
target_link_libraries(test_dialog PRIVATE dialog::dialog)
