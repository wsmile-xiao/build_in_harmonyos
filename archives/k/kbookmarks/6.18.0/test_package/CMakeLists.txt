cmake_minimum_required(VERSION 3.15)
project(test_kbookmarks CXX)

find_package(Qt6 REQUIRED COMPONENTS Core Gui Widgets Xml)
find_package(KF6Bookmarks REQUIRED)

add_executable(test_kbookmarks test.cpp)
target_link_libraries(test_kbookmarks KF6::Bookmarks KF6::BookmarksWidgets)

enable_testing()
add_test(NAME test_kbookmarks COMMAND test_kbookmarks)
set_tests_properties(test_kbookmarks PROPERTIES
    ENVIRONMENT "QT_QPA_PLATFORM=offscreen"
)
