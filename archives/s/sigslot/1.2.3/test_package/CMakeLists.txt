cmake_minimum_required(VERSION 3.15)
project(sigslot_consumer CXX)

find_package(PalSigslot CONFIG REQUIRED)

add_executable(sigslot_consumer test_sigslot.cpp)
target_link_libraries(sigslot_consumer PRIVATE Pal::Sigslot)
target_compile_features(sigslot_consumer PRIVATE cxx_std_14)
