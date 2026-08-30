cmake_minimum_required(VERSION 3.15)
project(test_mygui CXX)

find_package(MyGUI REQUIRED)

add_executable(test_mygui test.cpp)
target_link_libraries(test_mygui MyGUI::MyGUI)

# r11: headless consumer functional tests (no display/renderer required)
add_executable(test_headless test_headless.cpp)
target_link_libraries(test_headless MyGUI::MyGUI)

enable_testing()
add_test(NAME test_mygui COMMAND test_mygui)
add_test(NAME test_headless COMMAND test_headless)