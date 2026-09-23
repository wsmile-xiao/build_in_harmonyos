cmake_minimum_required(VERSION 3.15)
project(test_cba LANGUAGES CXX)

# cba 0.3.6 test harness — 11 cases / 55 assertions:
#   6 structural-analysis analytic checks (41 assertions)
#   4 CLI parameter / error-path cases    (8 assertions)
#   1 -o/-p output & plot consistency     (6 assertions)
# Upstream ships no tests (no tests/, no make check target, no configure.ac).
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

add_executable(test_cba test_cba.cpp)
