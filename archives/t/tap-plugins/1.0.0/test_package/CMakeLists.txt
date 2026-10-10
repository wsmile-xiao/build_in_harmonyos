cmake_minimum_required(VERSION 3.15)
project(tap_plugins_test C)

find_package(tap-plugins CONFIG REQUIRED)

add_executable(test_tap_plugins test_tap_plugins.c)
target_compile_features(test_tap_plugins PRIVATE c_std_99)
target_link_libraries(test_tap_plugins PRIVATE
    tap-plugins::tap-plugins
    ${CMAKE_DL_LIBS}
    m
)
