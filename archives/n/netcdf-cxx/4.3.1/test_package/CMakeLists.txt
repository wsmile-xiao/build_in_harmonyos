cmake_minimum_required(VERSION 3.15)
project(test_netcdfcxx CXX)

find_package(netcdf-cxx REQUIRED)

add_executable(test_netcdfcxx test.cpp)
target_link_libraries(test_netcdfcxx netcdf-cxx::netcdf-cxx)