cmake_minimum_required(VERSION 3.16)
project(test_qqc2 LANGUAGES CXX)

find_package(Qt6 REQUIRED COMPONENTS Core Qml Quick)

add_executable(test_qqc2 test_qqc2.cpp)
target_compile_features(test_qqc2 PRIVATE cxx_std_20)
target_link_libraries(test_qqc2 PRIVATE Qt6::Core Qt6::Qml Qt6::Quick)

if(CMAKE_CXX_COMPILER_ID MATCHES "Clang|GNU")
    target_link_options(test_qqc2 PRIVATE "-Wl,-rpath,$ORIGIN" "-Wl,--disable-new-dtags")
endif()

enable_testing()
add_test(NAME test_qqc2 COMMAND $<TARGET_FILE:test_qqc2>)
