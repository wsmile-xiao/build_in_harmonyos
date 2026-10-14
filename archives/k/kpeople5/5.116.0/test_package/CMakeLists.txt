cmake_minimum_required(VERSION 3.16)
project(test_kpeople5 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# Same aggregated-Qt5 wiring as the library build: the recipe's
# package_info exposes the project-installed KF5PeopleConfig.cmake
# (cmake_find_mode=none), so the test consumes it through
# CMAKE_PREFIX_PATH.
find_package(Qt5 5.15.2 REQUIRED COMPONENTS Core Gui Widgets Sql)
find_package(KF5People 5.116.0 REQUIRED)

add_executable(test_kpeople5 test.cpp)
target_link_libraries(test_kpeople5 PRIVATE Qt5::Core Qt5::Gui Qt5::Widgets KF5::People)

# /proc/self/maps reports the bare soname on OHOS, so give the test the real
# packaged library path to assert its ELF adaptation properties (R53).
target_compile_definitions(test_kpeople5 PRIVATE
    KPEOPLE_SO_PATH="$<TARGET_FILE:KF5::People>")

enable_testing()
add_test(NAME test_kpeople5 COMMAND test_kpeople5)
