cmake_minimum_required(VERSION 3.16)
project(mpich_component_consumers LANGUAGES C)

set(MPICH_EXECUTABLE_SUFFIX "" CACHE STRING "Validated MPICH consumer suffix")
if(NOT MPICH_EXECUTABLE_SUFFIX STREQUAL "" AND
   NOT MPICH_EXECUTABLE_SUFFIX STREQUAL "_relocated")
  message(FATAL_ERROR "Unexpected MPICH consumer suffix")
endif()

find_package(MPICH CONFIG REQUIRED)

foreach(required_target IN ITEMS MPI::MPI_C MPI::MPI_Fortran)
  if(NOT TARGET "${required_target}")
    message(FATAL_ERROR "Missing generated MPICH target: ${required_target}")
  endif()
endforeach()

if(NOT DEFINED MPICH_FORTRAN_OBJECT OR NOT EXISTS "${MPICH_FORTRAN_OBJECT}")
  message(FATAL_ERROR "The independently compiled Fortran object is missing")
endif()

add_executable(cmake_mpi_c cmake_c_consumer.c)
target_link_libraries(cmake_mpi_c PRIVATE MPI::MPI_C)
set_target_properties(
  cmake_mpi_c
  PROPERTIES OUTPUT_NAME "cmake_mpi_c${MPICH_EXECUTABLE_SUFFIX}"
)

add_executable(
  cmake_mpi_fortran
  cmake_fortran_driver.c
  "${MPICH_FORTRAN_OBJECT}"
)
set_source_files_properties(
  "${MPICH_FORTRAN_OBJECT}"
  PROPERTIES EXTERNAL_OBJECT TRUE GENERATED TRUE
)
# The C linker must obtain libmpifort, libmpi, and the Flang runtime solely
# from the generated component target. mpifort is used only for -c.
target_link_libraries(cmake_mpi_fortran PRIVATE MPI::MPI_Fortran)
set_target_properties(
  cmake_mpi_fortran
  PROPERTIES OUTPUT_NAME "cmake_mpi_fortran${MPICH_EXECUTABLE_SUFFIX}"
)
