cmake_minimum_required(VERSION 3.16)
project(test_kirigami LANGUAGES CXX)

find_package(Qt6 REQUIRED COMPONENTS Core Gui Qml Quick QuickControls2)
find_package(KF6Kirigami REQUIRED CONFIG)

add_executable(test_kirigami test_kirigami.cpp)
target_compile_features(test_kirigami PRIVATE cxx_std_20)
target_link_libraries(test_kirigami PRIVATE Qt6::Core Qt6::Gui Qt6::Qml Qt6::Quick Qt6::QuickControls2 KF6::Kirigami)

add_executable(test_kirigami_harmonyos test_kirigami_harmonyos.cpp)
target_compile_features(test_kirigami_harmonyos PRIVATE cxx_std_20)
target_link_libraries(test_kirigami_harmonyos PRIVATE Qt6::Core KF6::Kirigami)

if(CMAKE_CXX_COMPILER_ID MATCHES "Clang|GNU")
    target_link_options(test_kirigami PRIVATE "-Wl,-rpath,$ORIGIN" "-Wl,--disable-new-dtags")
endif()

enable_testing()
add_test(NAME test_kirigami COMMAND $<TARGET_FILE:test_kirigami>)
add_test(NAME kirigami_harmonyos_platform COMMAND $<TARGET_FILE:test_kirigami_harmonyos>)
