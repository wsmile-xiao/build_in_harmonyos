cmake_minimum_required(VERSION 3.15)
project(rhvoice_consumer CXX)

find_package(rhvoice CONFIG REQUIRED)

add_executable(rhvoice_consumer src/consumer.cpp)
target_compile_features(rhvoice_consumer PRIVATE cxx_std_11)
target_link_libraries(rhvoice_consumer PRIVATE rhvoice::rhvoice)
