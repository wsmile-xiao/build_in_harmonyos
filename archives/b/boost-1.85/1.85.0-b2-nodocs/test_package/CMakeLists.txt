cmake_minimum_required(VERSION 3.15)
project(test_boost LANGUAGES CXX)

find_package(Boost REQUIRED COMPONENTS
    atomic chrono filesystem iostreams program_options
    random regex system thread)

add_executable(test_boost src/test_boost.cpp)
target_link_libraries(test_boost PRIVATE
    Boost::atomic Boost::chrono Boost::filesystem Boost::iostreams
    Boost::program_options Boost::random Boost::regex Boost::system
    Boost::thread)
target_compile_features(test_boost PRIVATE cxx_std_17)
