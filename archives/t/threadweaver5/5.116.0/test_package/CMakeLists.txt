cmake_minimum_required(VERSION 3.16)
project(test_threadweaver5 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

set(CMAKE_AUTOMOC ON)

find_package(Qt5 5.15.2 REQUIRED COMPONENTS Core)
find_package(KF5ThreadWeaver 5.116.0 REQUIRED)

add_executable(test_threadweaver5 test.cpp)
target_link_libraries(test_threadweaver5 PRIVATE Qt5::Core KF5::ThreadWeaver)

# /proc/self/maps reports the bare soname on OHOS, so give the test the real
# packaged library path to assert its ELF adaptation properties (R53).
target_compile_definitions(test_threadweaver5 PRIVATE
    THREADWEAVER_SO_PATH="$<TARGET_FILE:KF5::ThreadWeaver>")

enable_testing()
add_test(NAME test_threadweaver5 COMMAND test_threadweaver5)
