cmake_minimum_required(VERSION 3.16)
project(test_libkomparediff2 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_AUTOMOC OFF)

find_package(Qt6 REQUIRED COMPONENTS Core Widgets)
find_package(KompareDiff2 REQUIRED)

add_executable(test_libkomparediff2 test.cpp)
# Upstream's install(EXPORT LibKompareDiff2Targets ...) passes no NAMESPACE,
# so the exported target is the plain, unnamespaced "KompareDiff2" (this is
# how upstream consumers, e.g. kompare, link it).
target_link_libraries(
    test_libkomparediff2
    PRIVATE
        Qt6::Core
        KompareDiff2
)

enable_testing()
add_test(NAME test_libkomparediff2 COMMAND test_libkomparediff2)
