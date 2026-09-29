cmake_minimum_required(VERSION 3.15)
project(libgridxc_consumer Fortran)

find_package(libgridxc CONFIG REQUIRED)

add_executable(lda_contract lda_contract.f90)
target_link_libraries(lda_contract PRIVATE libgridxc::libgridxc)

add_executable(gga_contract gga_contract.f90)
target_link_libraries(gga_contract PRIVATE libgridxc::libgridxc)
