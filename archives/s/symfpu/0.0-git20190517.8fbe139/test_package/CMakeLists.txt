cmake_minimum_required(VERSION 3.15)
project(symfpu_consumer_test LANGUAGES CXX)

find_package(symfpu CONFIG REQUIRED)

add_executable(test_symfpu
    test.cpp
    backend/src/simpleExecutable.cpp
)
target_include_directories(test_symfpu PRIVATE
    "${CMAKE_CURRENT_SOURCE_DIR}/backend/include"
)
target_compile_features(test_symfpu PRIVATE cxx_std_11)
target_link_libraries(test_symfpu PRIVATE symfpu::symfpu)