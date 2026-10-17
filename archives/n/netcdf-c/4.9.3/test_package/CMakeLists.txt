cmake_minimum_required(VERSION 3.15)
project(test_netcdf-c C)

find_package(netCDF REQUIRED)

add_executable(test_netcdf-c test.c)
target_link_libraries(test_netcdf-c netCDF::netcdf)

add_executable(ohos_specific_test ohos_specific_test.c)
target_link_libraries(ohos_specific_test netCDF::netcdf)

enable_testing()
add_test(NAME test_netcdf-c COMMAND test_netcdf-c)
add_test(NAME ohos_specific_test COMMAND ohos_specific_test)