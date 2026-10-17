cmake_minimum_required(VERSION 3.15)
project(test_boost_log_setup CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# The boost1.84-log_setup component package publishes its own CMakeDeps
# config (BoostLogSetup) to avoid colliding with the boost/1.84.0 umbrella
# package's Boost config file. Component targets keep the Boost:: namespace
# via the cmake_target_name property.
find_package(BoostLogSetup REQUIRED CONFIG)

add_executable(test_log_setup test_log_setup.cpp)
target_link_libraries(test_log_setup PRIVATE Boost::log_setup)

enable_testing()
add_test(NAME boost_log_setup_test COMMAND test_log_setup)
