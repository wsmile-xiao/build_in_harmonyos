cmake_minimum_required(VERSION 3.15)
project(test_kglobalaccel LANGUAGES CXX)

# Consumer test for kglobalaccel (R34: real API usage, no stub test).
# The 13 assertions in test.cpp (declared in test_package/MANIFEST.yml) are
# written against API consistency and the client-side registration chain
# (not D-Bus side effects), so they are deterministic both on desktop
# sessions and headless OHOS devices:
#   1. KGlobalAccel::self() != nullptr
#   2. hasShortcut() is false before registration
#   3. hasShortcut() after setShortcut() equals the setShortcut() result
#   4. setDefaultShortcut() accepts a well-formed sequence
#   5. defaultShortcut() round-trips the registered sequence
#   6. setShortcut() rejects an action without objectName()
#   7. rejected action stays unregistered
#   8. setShortcut() refuses a sequence with a garbage keycode (-1)
#   9. garbage-keycode sequence stays unregistered
#  10. shortcut() returns at most the requested sequence
#  11. isGlobalShortcutAvailable() is idempotent for the same sequence
#  12. hasShortcut() is false after removeAllShortcuts()
#  13. defaultShortcut() is empty after removeAllShortcuts()
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(KF5GlobalAccel REQUIRED)
find_package(Qt5 REQUIRED COMPONENTS Widgets)

add_executable(test_kglobalaccel test.cpp)
target_link_libraries(test_kglobalaccel KF5::GlobalAccel Qt5::Widgets)

enable_testing()
add_test(NAME test_kglobalaccel COMMAND test_kglobalaccel)
