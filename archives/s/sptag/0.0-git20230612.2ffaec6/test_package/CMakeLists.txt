cmake_minimum_required(VERSION 3.15)
project(test_sptag CXX)

find_package(sptag REQUIRED)

add_executable(test_sptag test_sptag.cpp)
target_link_libraries(test_sptag sptag::sptag)

# Static OpenMP on Clang (same rationale as the main recipe's build():
# libomp.so is not on the loader path and dir discovery returned NONE on
# the harmonybrew layout). -static-openmp embeds the runtime so test_sptag
# starts without LD_LIBRARY_PATH/RPATH. Clang-only: GCC builds keep shared
# -fopenmp. The SPTAG_OMP_RPATH block below stays as fallback.
if(CMAKE_CXX_COMPILER_ID MATCHES "Clang")
    target_compile_options(test_sptag PRIVATE -static-openmp)
    target_link_options(test_sptag PRIVATE -static-openmp)
endif()

# OHOS SDK libomp is not on the default loader path: when the recipe
# provides SPTAG_OMP_RPATH (absolute dir containing libomp.so), embed it
# as RUNPATH so the consumer binary resolves libomp.so without relying on
# LD_LIBRARY_PATH propagation (which does not reach every run context).
if(SPTAG_OMP_RPATH)
    target_link_options(test_sptag PRIVATE "LINKER:-rpath,${SPTAG_OMP_RPATH}")
endif()

enable_testing()
add_test(NAME test_sptag COMMAND test_sptag)
