cmake_minimum_required(VERSION 3.15)
project(test_package C)

find_package(ed25519 CONFIG REQUIRED)

add_executable(test_ed25519 test_ed25519.c)
target_link_libraries(test_ed25519 PRIVATE ed25519::ed25519)
target_compile_features(test_ed25519 PRIVATE c_std_99)
