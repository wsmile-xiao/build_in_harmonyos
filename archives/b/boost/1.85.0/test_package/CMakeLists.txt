cmake_minimum_required(VERSION 3.15)
project(test_boost CXX)

find_package(Boost REQUIRED CONFIG COMPONENTS filesystem regex program_options iostreams)

add_executable(test_boost test_boost.cpp)
target_link_libraries(test_boost PRIVATE Boost::filesystem Boost::regex Boost::program_options Boost::iostreams)

enable_testing()
add_test(NAME boost_test COMMAND test_boost)
