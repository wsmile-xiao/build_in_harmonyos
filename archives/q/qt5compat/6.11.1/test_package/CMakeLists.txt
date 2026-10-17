cmake_minimum_required(VERSION 3.15)
project(test_qt5compat CXX)

# Use Qt6 module system to find Qt6::Core5Compat via the installed
# Qt6Core5CompatConfig.cmake (provided by the qt5compat package).
find_package(Qt6 COMPONENTS Core5Compat REQUIRED)

add_executable(test_qt5compat test.cpp)
target_link_libraries(test_qt5compat Qt6::Core5Compat)

enable_testing()
add_test(NAME test_qt5compat COMMAND test_qt5compat)