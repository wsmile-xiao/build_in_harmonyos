cmake_minimum_required(VERSION 3.15)
project(actor_framework_package_test LANGUAGES CXX)

find_package(actor-framework REQUIRED CONFIG)

add_executable(actor_probe actor_probe.cpp)
target_compile_features(actor_probe PRIVATE cxx_std_11)
target_link_libraries(actor_probe PRIVATE actor-framework::actor-framework)
