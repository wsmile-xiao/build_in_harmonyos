cmake_minimum_required(VERSION 3.15)
project(test_vampire C)

# vampire is a binary tool, not a library — no find_package needed
# The smoke test runs the vampire binary directly

enable_testing()
