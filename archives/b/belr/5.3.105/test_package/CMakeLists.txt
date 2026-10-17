cmake_minimum_required(VERSION 3.15)
project(test_belr CXX)

# Consumer links the packaged library. belr/belr.h and belr/parser.h include
# bctoolbox headers, and the generated CMakeDeps config of the Belledonne
# packages does not put the transitive bctoolbox include dir on the compile
# line, so the dependency is found and linked explicitly - the same handling
# documented in the bzrtp/5.3.105 test_package (which hit this on device).
find_package(Belr REQUIRED)
find_package(bctoolbox REQUIRED)

add_executable(test_belr test_belr.cpp)
target_link_libraries(test_belr PRIVATE Belr::belr bctoolbox::bctoolbox)
set_target_properties(test_belr PROPERTIES CXX_STANDARD 17 CXX_STANDARD_REQUIRED ON CXX_EXTENSIONS OFF)
