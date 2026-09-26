cmake_minimum_required(VERSION 3.15)
project(test_kglobalaccel5 LANGUAGES CXX)

# Consumer test for kglobalaccel5 (R34: real API usage, no stub test).
# The 6 assertions in test.cpp (declared in test_package/MANIFEST.yml) are
# written against API consistency (not D-Bus side effects), so they are
# deterministic both on desktop sessions and headless OHOS devices:
#   1. KGlobalAccel::self() != nullptr
#   2. hasShortcut() is false before registration
#   3. hasShortcut() after setShortcut() equals the setShortcut() result
#   4. shortcut() returns at most the requested sequence
#   5. isGlobalShortcutAvailable() is idempotent for the same sequence
#   6. hasShortcut() is false after removeAllShortcuts()
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# C++17: matches the ohos-aarch64 profile cppstd and the KF5GlobalAccel
# package requirements; REQUIRED ON so a mismatch fails loudly at configure
# time instead of silently degrading.

# R34 traceability: the 6 assertions exercised by test.cpp are declared in
# test_package/MANIFEST.yml (test_package_tests[0], assertion_count: 6).
# Each check() in test.cpp maps 1:1 to that declaration; a non-zero exit from
# the consumer binary fails the conan test_package stage.

find_package(KF5GlobalAccel REQUIRED)
find_package(Qt5 REQUIRED COMPONENTS Widgets)

add_executable(test_kglobalaccel5 test.cpp)
target_link_libraries(test_kglobalaccel5 KF5::GlobalAccel Qt5::Widgets)

enable_testing()
add_test(NAME test_kglobalaccel5 COMMAND test_kglobalaccel5)
