cmake_minimum_required(VERSION 3.15)
project(test_librsb C CXX)

# Resolve the librsb package (transitive zlib include/lib paths propagate
# automatically through the imported target) via Conan generators.
find_package(librsb REQUIRED)

add_executable(test_librsb test_librsb.c)
target_link_libraries(test_librsb PRIVATE librsb::librsb)

# librsb static archive embeds OpenMP-offloaded objects (__kmpc_*/omp_*)
# and C++ objects (rsbpp_coo.cpp, std::__n1::vector). A pure-C link line
# therefore fails with undefined __kmpc_* plus operator delete(void*).
# Link the OpenMP runtime (CMake module picks the correct -fopenmp/-lomp
# for the OHOS clang; raw -fopenmp fallback when the module misses in
# cross-compiling) and drive the final link with the C++ linker.
find_package(OpenMP)
if(OpenMP_C_FOUND)
  target_link_libraries(test_librsb PRIVATE OpenMP::OpenMP_C)
else()
  target_compile_options(test_librsb PRIVATE -fopenmp)
  target_link_options(test_librsb PRIVATE -fopenmp)
endif()
if(OpenMP_CXX_FOUND)
  target_link_libraries(test_librsb PRIVATE OpenMP::OpenMP_CXX)
endif()
# Force C++ linker so libc++ runtime resolves operator delete without
# renaming the C test source (C API static archive with C++ impl).
set_target_properties(test_librsb PROPERTIES LINKER_LANGUAGE CXX)

enable_testing()
add_test(NAME test_librsb COMMAND test_librsb)
