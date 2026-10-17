cmake_minimum_required(VERSION 3.15)
project(test_boost_ext_ut CXX)

find_package(ut REQUIRED)

# consumer suite written with boost.ut itself: must pass (exit 0)
add_executable(test_boost_ext_ut test_boost_ext_ut.cpp)
target_link_libraries(test_boost_ext_ut PRIVATE Boost::ut)
target_compile_features(test_boost_ext_ut PRIVATE cxx_std_20)

# negative probe: contains one deliberately failing expectation, must exit non-zero
add_executable(test_boost_ext_ut_negative test_boost_ext_ut_negative.cpp)
target_link_libraries(test_boost_ext_ut_negative PRIVATE Boost::ut)
target_compile_features(test_boost_ext_ut_negative PRIVATE cxx_std_20)
