cmake_minimum_required(VERSION 3.16)
project(qt6_harmonyos_uid_probe LANGUAGES CXX)

add_executable(qt6_uid_probe_unit probe_unit_test.cpp)
target_compile_features(qt6_uid_probe_unit PRIVATE cxx_std_17)
target_compile_options(qt6_uid_probe_unit PRIVATE -Wno-unused-command-line-argument)
target_sources(qt6_uid_probe_unit PRIVATE socket_probe.cpp)
