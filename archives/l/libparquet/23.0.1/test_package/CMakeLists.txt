cmake_minimum_required(VERSION 3.15)
project(test_package LANGUAGES CXX)

find_package(Parquet REQUIRED CONFIG)

add_executable(${PROJECT_NAME} test_package.cpp)

if (TARGET Parquet::parquet_shared)
    target_link_libraries(${PROJECT_NAME} PRIVATE Parquet::parquet_shared)
else()
    target_link_libraries(${PROJECT_NAME} PRIVATE Parquet::parquet_static)
endif()

target_compile_features(${PROJECT_NAME} PRIVATE cxx_std_20)
