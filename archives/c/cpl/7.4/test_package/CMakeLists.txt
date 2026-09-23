cmake_minimum_required(VERSION 3.15)
project(test_cpl C)

find_package(cpl REQUIRED)
find_package(libcext REQUIRED)
find_package(cfitsio REQUIRED)
find_package(wcslib REQUIRED)
find_package(ZLIB REQUIRED)

add_executable(test_cpl test_cpl.c)
target_link_libraries(test_cpl cpl::cpl libcext::libcext cfitsio::cfitsio wcslib::wcslib ZLIB::ZLIB)
