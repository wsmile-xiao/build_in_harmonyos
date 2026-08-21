cmake_minimum_required(VERSION 3.15)
project(vamp_smoke CXX)

find_package(vamp-plugin-sdk CONFIG REQUIRED)

add_executable(vamp_smoke main.cpp)
target_link_libraries(vamp_smoke PRIVATE vamp-plugin-sdk::vamp-plugin-sdk)

enable_testing()
add_test(NAME vamp_smoke COMMAND vamp_smoke)
