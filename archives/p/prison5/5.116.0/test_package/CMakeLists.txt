cmake_minimum_required(VERSION 3.16)
project(test_prison5 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# Same native-Qt5 wiring as the library build: the recipe's package_info
# exposes the project-installed KF5PrisonConfig.cmake (cmake_find_mode=none),
# so the test consumes it through CMAKE_PREFIX_PATH.
find_package(Qt5 5.15.2 REQUIRED COMPONENTS Core Gui)
find_package(KF5Prison 5.116.0 REQUIRED)

add_executable(test_prison5 test.cpp)
target_link_libraries(test_prison5 PRIVATE Qt5::Core Qt5::Gui KF5::Prison)

# /proc/self/maps reports the bare soname on OHOS, so give the test the real
# packaged library path to assert its ELF adaptation properties (R53).
target_compile_definitions(test_prison5 PRIVATE
    PRISON_SO_PATH="$<TARGET_FILE:KF5::Prison>")

enable_testing()
add_test(NAME test_prison5 COMMAND test_prison5)
