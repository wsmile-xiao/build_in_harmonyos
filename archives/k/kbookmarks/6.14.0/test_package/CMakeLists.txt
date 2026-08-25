cmake_minimum_required(VERSION 3.15)
project(test_kbookmarks CXX)

find_package(KF6Bookmarks REQUIRED)

add_executable(test_kbookmarks test.cpp)
target_link_libraries(test_kbookmarks KF6::Bookmarks)

enable_testing()
add_test(NAME test_kbookmarks COMMAND test_kbookmarks)
