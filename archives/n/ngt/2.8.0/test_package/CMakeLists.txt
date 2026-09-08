cmake_minimum_required(VERSION 3.15)
project(test_package CXX)

# Consumer tests: compile against the packaged NGT headers with OpenMP enabled
# (NGT headers use <omp.h>/#pragma omp), link the packaged library.
# The suite is split into one executable per scenario so each NGT functional
# area (distance type / object type / graph type / persistence / CRUD / batch
# search / property round-trip / error paths) can fail independently and be
# identified in the CI log.
find_package(OpenMP REQUIRED)
find_package(ngt CONFIG REQUIRED)

# Baseline target keeps its original source file name test.cpp (target
# test_ngt) so it is unchanged from the pre-existing single-scenario test.
add_executable(test_ngt test.cpp)
target_link_libraries(test_ngt PRIVATE ngt::ngt OpenMP::OpenMP_CXX)

set(NGT_TEST_TARGETS
    test_distance      # distance-type matrix (L1/L2/Angle/Cosine)
    test_objecttype    # object-type matrix (Float/Uint8, L2/Hamming)
    test_graph         # graph-type matrix (ANNG/ONNG/IANNG)
    test_persist       # save/reopen (rw + readonly) consistency
    test_crud          # append + remove + search-after-delete
    test_batch         # multiple queries in one index session
    test_property      # getProperty/setProperty round-trip
    test_errors        # error/boundary paths throw NGT::Exception
)

foreach(tgt IN LISTS NGT_TEST_TARGETS)
    add_executable(${tgt} ${tgt}.cpp)
    target_link_libraries(${tgt} PRIVATE ngt::ngt OpenMP::OpenMP_CXX)
endforeach()
