cmake_minimum_required(VERSION 3.15)
project(geogram_test LANGUAGES CXX)

find_package(geogram CONFIG REQUIRED)

add_executable(geogram_probe test_package.cpp)
set_target_properties(geogram_probe PROPERTIES
    RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/bin"
)
target_compile_features(geogram_probe PRIVATE cxx_std_17)
target_link_libraries(geogram_probe PRIVATE geogram::geogram)

