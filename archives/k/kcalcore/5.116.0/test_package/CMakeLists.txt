cmake_minimum_required(VERSION 3.16)
project(test_kcalcore LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# Same native-config wiring as the library build: the recipe's package_info
# exposes the project-installed KF5CalendarCoreConfig.cmake
# (cmake_find_mode=none), so the test consumes it through CMAKE_PREFIX_PATH.
find_package(Qt5 5.15.2 REQUIRED COMPONENTS Core Gui)
find_package(KF5CalendarCore 5.116.0 REQUIRED)

add_executable(test_kcalcore test.cpp)
target_link_libraries(test_kcalcore PRIVATE Qt5::Core Qt5::Gui KF5::CalendarCore)

# /proc/self/maps reports kernel-side HMDFS paths that cannot be re-opened;
# hand the test the consumer-view packaged library path so it can parse the
# ELF dynamic segment directly (R53; kpeople5 KPEOPLE_SO_PATH precedent).
target_compile_definitions(test_kcalcore PRIVATE
    KCALCORE_SO_PATH="$<TARGET_FILE:KF5::CalendarCore>")

enable_testing()
add_test(NAME test_kcalcore COMMAND test_kcalcore)
