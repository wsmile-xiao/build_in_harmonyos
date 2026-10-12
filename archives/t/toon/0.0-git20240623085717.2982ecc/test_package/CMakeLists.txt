cmake_minimum_required(VERSION 3.15)
project(toon_consumer LANGUAGES CXX)

find_package(toon CONFIG REQUIRED)
add_executable(toon_consumer src/consumer.cpp)
target_compile_features(toon_consumer PRIVATE cxx_std_14)
target_link_libraries(toon_consumer PRIVATE toon::toon)
