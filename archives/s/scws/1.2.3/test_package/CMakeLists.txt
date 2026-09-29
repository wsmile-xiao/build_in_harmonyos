cmake_minimum_required(VERSION 3.15)
project(test_scws C)

find_package(scws CONFIG REQUIRED)

# Consumer-level API checks (T1-T7, OHOS-specific mmap/flock included)
add_executable(test_scws test.c)
target_link_libraries(test_scws PRIVATE scws::scws)

# Replay of the 17 upstream cases from phpext/scws_test.php
add_executable(upstream_test upstream_test.c)
target_link_libraries(upstream_test PRIVATE scws::scws)
