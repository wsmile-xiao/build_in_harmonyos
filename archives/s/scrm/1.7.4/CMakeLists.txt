cmake_minimum_required(VERSION 3.15)
project(scrm VERSION 1.7.4 LANGUAGES CXX)
include(GNUInstallDirs)
option(SCRM_BUILD_TESTS "Build the complete upstream registered suites" ON)
set(core_sources
    src/param.cc src/forest.cc src/node.cc src/node_container.cc
    src/time_interval.cc src/model.cc src/tree_point.cc
    src/random/random_generator.cc src/random/mersenne_twister.cc src/random/fastfunc.cc
    src/summary_statistics/tmrca.cc src/summary_statistics/seg_sites.cc
    src/summary_statistics/frequency_spectrum.cc src/summary_statistics/newick_tree.cc
    src/summary_statistics/oriented_forest.cc)
add_library(scrm_core OBJECT ${core_sources})
target_compile_features(scrm_core PUBLIC cxx_std_11)
target_compile_definitions(scrm_core PUBLIC VERSION="${PROJECT_VERSION}" NDEBUG)
add_executable(scrm src/scrm.cc)
target_link_libraries(scrm PRIVATE scrm_core)
install(TARGETS scrm RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR})
install(FILES doc/scrm.1 DESTINATION ${CMAKE_INSTALL_MANDIR}/man1)
if(SCRM_BUILD_TESTS)
    enable_testing()
    find_package(cppunit CONFIG REQUIRED)
    set(unit_sources
        tests/unittests/test_forest.cc tests/unittests/test_model.cc
        tests/unittests/test_node.cc tests/unittests/test_node_container.cc
        tests/unittests/test_time_interval.cc tests/unittests/test_fastfunc.cc
        tests/unittests/test_param.cc tests/unittests/test_random_generator.cc
        tests/unittests/test_summary_statistics.cc tests/unittests/test_contemporaries_container.cc)
    # UNITTEST changes the upstream debug implementation: do not share the
    # production object library with this suite.
    add_executable(unit_tests ${core_sources} ${unit_sources}
        src/random/constant_generator.cc src/forest-debug.cc tests/cppunit/test_runner.cc)
    target_compile_features(unit_tests PRIVATE cxx_std_11)
    target_compile_definitions(unit_tests PRIVATE UNITTEST NDEBUG VERSION="${PROJECT_VERSION}")
    target_link_libraries(unit_tests PRIVATE cppunit::cppunit)
    add_executable(algorithm_tests tests/algorithmtest/test_algorithm.cc tests/cppunit/test_runner.cc)
    target_link_libraries(algorithm_tests PRIVATE scrm_core cppunit::cppunit)
    add_test(NAME unit_tests COMMAND unit_tests)
    add_test(NAME algorithm_tests COMMAND algorithm_tests)
    set_tests_properties(unit_tests algorithm_tests PROPERTIES TIMEOUT 900)
endif()
