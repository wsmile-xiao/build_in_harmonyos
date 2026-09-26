cmake_minimum_required(VERSION 3.15)
project(test_superlu_dist C)

# Find the package via the Conan-generated CMakeDeps config
# (cmake_file_name = "superlu-dist", from conanfile.py package_info).
find_package(superlu-dist REQUIRED)

add_executable(test_superlu_dist test.c)

# MPI comes in transitively: the SuperLU_DIST package declares its MPI
# dependency, so the generated target carries MPI::MPI_C in its interface
# (providing both mpi.h and libmpi). Linking the solver target is therefore
# enough -- no separate find_package(MPI) is needed, which matters because
# CMake's own FindMPI cannot resolve the MPI wrappers on OHOS.
target_link_libraries(test_superlu_dist PRIVATE superlu-dist::superlu-dist)
