cmake_minimum_required(VERSION 3.16)
project(test_boost_morpheus_components LANGUAGES CXX)

find_package(
    Boost 1.90.0 CONFIG REQUIRED
    COMPONENTS filesystem program_options system unit_test_framework
)

add_executable(test_boost_morpheus_components test.cpp)
target_compile_features(test_boost_morpheus_components PRIVATE cxx_std_17)
target_link_libraries(
    test_boost_morpheus_components
    PRIVATE Boost::filesystem Boost::program_options Boost::system
)

# Boost.Test dynamic-link consumer — mirrors the pinocchio 4.1.0 upstream
# unittest pattern: find_package(Boost COMPONENTS unit_test_framework)
# + BOOST_TEST_DYN_LINK, links Boost::unit_test_framework.
add_executable(test_boost_unit_test_framework test_unit_test_framework.cpp)
target_compile_features(test_boost_unit_test_framework PRIVATE cxx_std_17)
target_compile_definitions(test_boost_unit_test_framework PRIVATE BOOST_TEST_DYN_LINK)
target_link_libraries(
    test_boost_unit_test_framework
    PRIVATE Boost::unit_test_framework
)
