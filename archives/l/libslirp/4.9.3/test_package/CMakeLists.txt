cmake_minimum_required(VERSION 3.16)
project(libslirp_consumer C)

find_package(libslirp CONFIG REQUIRED)

add_executable(libslirp_consumer test_package.c)
target_compile_features(libslirp_consumer PRIVATE c_std_99)
target_link_libraries(libslirp_consumer PRIVATE libslirp::slirp)
