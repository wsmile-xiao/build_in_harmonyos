cmake_minimum_required(VERSION 3.15)
project(test_zita_resampler LANGUAGES CXX)

find_package(libzita-resampler CONFIG REQUIRED)
add_executable(test_zita_resampler test_zita_resampler.cpp)
target_link_libraries(test_zita_resampler PRIVATE libzita-resampler::libzita-resampler)
