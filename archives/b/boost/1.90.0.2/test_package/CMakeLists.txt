cmake_minimum_required(VERSION 3.16)
project(test_boost_morpheus_components LANGUAGES CXX)

find_package(
    Boost 1.90.0 CONFIG REQUIRED
    COMPONENTS filesystem program_options system
)

add_executable(test_boost_morpheus_components test.cpp)
target_compile_features(test_boost_morpheus_components PRIVATE cxx_std_17)
target_link_libraries(
    test_boost_morpheus_components
    PRIVATE Boost::filesystem Boost::program_options Boost::system
)
