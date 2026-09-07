cmake_minimum_required(VERSION 3.15)
project(libsass_consumer LANGUAGES CXX)

find_package(libsass CONFIG REQUIRED)
add_executable(libsass_consumer consumer.cpp)
target_link_libraries(libsass_consumer PRIVATE libsass::libsass)
