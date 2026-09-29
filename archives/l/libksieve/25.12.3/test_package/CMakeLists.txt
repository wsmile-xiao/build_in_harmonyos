cmake_minimum_required(VERSION 3.16)
project(test_libksieve LANGUAGES CXX)

find_package(Qt6 REQUIRED COMPONENTS Core)
find_package(KF6I18n REQUIRED CONFIG)
find_package(KPim6KSieve REQUIRED CONFIG)

add_executable(test_libksieve test_libksieve.cpp)
target_compile_features(test_libksieve PRIVATE cxx_std_20)
target_link_options(test_libksieve PRIVATE "-Wl,--as-needed")
target_link_libraries(test_libksieve PRIVATE Qt6::Core KF6::I18n KPim6::KSieve)

enable_testing()
add_test(NAME test_libksieve COMMAND $<TARGET_FILE:test_libksieve>)
