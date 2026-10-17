cmake_minimum_required(VERSION 3.15)
project(test_netcdf_fortran LANGUAGES C Fortran)

find_package(netCDF-Fortran REQUIRED)

# Fortran 消费者：真实读写链路（建 netCDF-4 文件、写属性、开 deflate、读写校验）
add_executable(test_netcdf_fortran test_netcdf_fortran.f90)
target_link_libraries(test_netcdf_fortran PRIVATE netCDF::netcdff)

# C 侧交付面契约测试：按 SONAME 以 RTLD_NOW 加载 libnetcdff.so 并解析 ABI 入口。
# 不链接 netcdff（故意用 dlopen 走运行期解析路径），只需 libdl。
add_executable(test_netcdf_fortran_abi test_netcdf_fortran_abi.c)
target_link_libraries(test_netcdf_fortran_abi PRIVATE ${CMAKE_DL_LIBS})
