cmake_minimum_required(VERSION 3.15)
project(libxcrypt_test_package C)

find_package(libxcrypt CONFIG REQUIRED)

add_executable(test_libxcrypt test_libxcrypt.c)
target_compile_features(test_libxcrypt PRIVATE c_std_11)
target_link_libraries(test_libxcrypt PRIVATE libxcrypt::crypt)
