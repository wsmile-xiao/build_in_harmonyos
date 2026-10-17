cmake_minimum_required(VERSION 3.16)
project(kholidays_test LANGUAGES CXX)

find_package(KF6Holidays REQUIRED)

add_executable(test_kholidays test_kholidays.cpp)
target_link_libraries(test_kholidays PRIVATE KF6::Holidays)
target_compile_features(test_kholidays PRIVATE cxx_std_20)
