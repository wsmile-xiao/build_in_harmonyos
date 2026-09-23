cmake_minimum_required(VERSION 3.16)
project(test_f3d CXX)

# Consumer-contract smoke test: the f3d package exports a CMake package
# config (f3dConfig.cmake + f3dLibraryTargets) and a runnable binary.
# We do not link libf3d here (the library headers require VTK types, and
# the packaged SDK dev files target application embedding); the test
# binary executes the packaged `f3d` executable instead, which loads
# libf3d.so + all VTK shared libraries through the dynamic linker —
# exercising the package's runtime contract (SONAME, re-sign, loader
# resolution) far more strictly than a link check would.
add_executable(test_f3d test_f3d.cpp)
