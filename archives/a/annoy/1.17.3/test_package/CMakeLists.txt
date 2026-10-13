cmake_minimum_required(VERSION 3.15)
project(annoy_test_package LANGUAGES CXX)

find_package(Annoy REQUIRED)

# Consumer test 1: ANN search round-trip over the Angular metric using a
# single-threaded build policy — the plain `#include <annoy/annoylib.h>` usage.
add_executable(annoy_consumer_angular test_angular.cpp)
target_link_libraries(annoy_consumer_angular PRIVATE Annoy::Annoy)

# Consumer test 2: multithreaded build policy + save/load on-disk round-trip
# (exercises the mmap path that OHOS resolves through <sys/mman.h>).
# ANNOYLIB_MULTITHREADED_BUILD is what upstream's setup.py defines for every
# Python 3 platform; it is what makes AnnoyIndexMultiThreadedBuildPolicy
# available. It needs Threads::Threads, i.e. -pthread.
find_package(Threads REQUIRED)
add_executable(annoy_consumer_ondisk test_ondisk.cpp)
target_compile_definitions(annoy_consumer_ondisk PRIVATE ANNOYLIB_MULTITHREADED_BUILD)
target_link_libraries(annoy_consumer_ondisk PRIVATE Annoy::Annoy Threads::Threads)
