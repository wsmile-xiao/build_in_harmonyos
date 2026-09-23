cmake_minimum_required(VERSION 3.15)
project(test_boost1_84_stacktrace_noop CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(boost1.84-stacktrace_noop REQUIRED CONFIG COMPONENTS stacktrace_noop)

add_executable(test_boost1_84_stacktrace_noop test_boost_stacktrace_noop.cpp)
target_link_libraries(test_boost1_84_stacktrace_noop
    PRIVATE boost1.84-stacktrace_noop::stacktrace_noop)
target_link_options(test_boost1_84_stacktrace_noop PRIVATE -static-libstdc++)

enable_testing()
add_test(NAME boost1_84_stacktrace_noop_test
    COMMAND test_boost1_84_stacktrace_noop)

if(BOOST_NOOP_TEST_OHOS)
    add_executable(test_boost1_84_stacktrace_noop_ohos test_ohos_noop.cpp)
    target_link_libraries(test_boost1_84_stacktrace_noop_ohos
        PRIVATE boost1.84-stacktrace_noop::stacktrace_noop)
    target_link_options(test_boost1_84_stacktrace_noop_ohos
        PRIVATE -static-libstdc++)
    add_test(NAME boost1_84_stacktrace_noop_ohos_test
        COMMAND test_boost1_84_stacktrace_noop_ohos)
endif()
