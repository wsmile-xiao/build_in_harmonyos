cmake_minimum_required(VERSION 3.16)
project(test_ksanecore CXX)

# KSaneCore6Config chains through Qt6Gui; load Qt6 first so the
# find_dependency(Qt6Gui) inside the config resolves.
find_package(Qt6 REQUIRED COMPONENTS Core Gui)
find_package(KSaneCore6 REQUIRED)

add_executable(test_ksanecore test.cpp)
target_link_libraries(test_ksanecore KSane6::Core)

enable_testing()
add_test(NAME test_ksanecore COMMAND test_ksanecore)
