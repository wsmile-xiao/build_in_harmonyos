cmake_minimum_required(VERSION 3.16)
project(test_kitemviews5 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

find_package(Qt5 5.15.2 REQUIRED COMPONENTS Core Gui Widgets)
find_package(KF5ItemViews 5.116.0 REQUIRED)

add_executable(test_kitemviews5 test.cpp)
target_link_libraries(test_kitemviews5 PRIVATE Qt5::Widgets KF5::ItemViews)

# /proc/self/maps reports the bare soname on OHOS, so give the test the real
# packaged library path to assert its ELF adaptation properties (R53).
target_compile_definitions(test_kitemviews5 PRIVATE
    KITEMVIEWS_SO_PATH="$<TARGET_FILE:KF5::ItemViews>")

enable_testing()
add_test(NAME test_kitemviews5 COMMAND test_kitemviews5)
