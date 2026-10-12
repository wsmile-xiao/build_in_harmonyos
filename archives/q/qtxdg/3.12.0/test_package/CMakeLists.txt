cmake_minimum_required(VERSION 3.15)
project(test_qtxdg CXX)

# Qt5Xdg is exported by the qtxdg package (upstream target name, no namespace).
find_package(Qt5Xdg REQUIRED)
# Qt5Core / Qt5Widgets come transitively through the qtxdg requirements.
find_package(Qt5 REQUIRED)

add_executable(test_qtxdg test_qtxdg.cpp)
target_link_libraries(test_qtxdg PRIVATE Qt5Xdg Qt5::Core Qt5::Widgets)

enable_testing()
add_test(NAME test_qtxdg COMMAND test_qtxdg)
