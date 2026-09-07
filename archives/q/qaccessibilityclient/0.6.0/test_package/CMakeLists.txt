cmake_minimum_required(VERSION 3.15)
project(test_qaccessibilityclient CXX)

# Consume the upstream-exported CMake package (cmake_find_mode=none in the
# recipe, so this resolves against the QAccessibilityClient6Config.cmake
# installed by the project itself).
find_package(QAccessibilityClient6 REQUIRED)
find_package(Qt6 COMPONENTS Core REQUIRED)

add_executable(test_qaccessibilityclient test_qaccessibilityclient.cpp)
# Upstream install(EXPORT ...) declares no NAMESPACE, so the exported
# IMPORTED target is the plain "QAccessibilityClient6" (the inspector
# consumes it the same way: target_link_libraries(... QAccessibilityClient6)).
target_link_libraries(test_qaccessibilityclient
    QAccessibilityClient6
    Qt6::Core
)

enable_testing()
add_test(NAME test_qaccessibilityclient COMMAND test_qaccessibilityclient)
