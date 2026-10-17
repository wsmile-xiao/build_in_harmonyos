cmake_minimum_required(VERSION 3.16)
project(test_kholidays5 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# Same native-config wiring as the library build: the recipe's package_info
# exposes the project-installed KF5HolidaysConfig.cmake (cmake_find_mode=none)
# and qt5-qtbase ships its native Qt5 configs, so the test consumes them
# through CMAKE_PREFIX_PATH (kcalcore test_package precedent).
find_package(Qt5 5.15.2 REQUIRED COMPONENTS Core)
find_package(KF5Holidays 5.116.0 REQUIRED)

add_executable(test_kholidays5 test.cpp)
target_link_libraries(test_kholidays5 PRIVATE Qt5::Core KF5::Holidays)

# /proc/self/maps reports kernel-side HMDFS paths that cannot be re-opened;
# hand the test the consumer-view packaged library path so it can parse the
# ELF dynamic segment directly (R53; kpeople5 KPEOPLE_SO_PATH precedent).
target_compile_definitions(test_kholidays5 PRIVATE
    KHOLIDAYS_SO_PATH="$<TARGET_FILE:KF5::Holidays>")

enable_testing()
add_test(NAME test_kholidays5 COMMAND test_kholidays5)
