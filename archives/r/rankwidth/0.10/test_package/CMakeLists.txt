cmake_minimum_required(VERSION 3.15)
project(test_rankwidth C)

find_package(rankwidth CONFIG REQUIRED)

add_executable(test_rankwidth test_rankwidth.c)
target_link_libraries(test_rankwidth PRIVATE rankwidth::rankwidth)

# Upstream regression smoke: igraph-free driver for the bundled
# example graphs (see upstream_smoke.c provenance header). It links the
# same packaged librw and runs the verbatim simplerw.c compute loop on
# vendored example_graphs data. Executed as ./upstream_smoke <graph>
# by test_package/conanfile.py (counts feed HMBS_UPSTREAM_TEST_RESULT).
# NOTE: no enable_testing()/add_test() here on purpose. Registering
# ctest entries would create a false ctest inventory that the evidence
# gate misreads as additional upstream tests (libarcus/5.0.0 precedent).
add_executable(upstream_smoke upstream_smoke.c)
target_link_libraries(upstream_smoke PRIVATE rankwidth::rankwidth)
