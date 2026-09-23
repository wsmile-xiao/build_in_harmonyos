cmake_minimum_required(VERSION 3.15)
project(blosc2_test C)
find_package(Blosc2 CONFIG REQUIRED)
add_executable(test_blosc2 test_blosc2.c)
target_link_libraries(test_blosc2 PRIVATE Blosc2::blosc2)
target_compile_features(test_blosc2 PRIVATE c_std_99)

