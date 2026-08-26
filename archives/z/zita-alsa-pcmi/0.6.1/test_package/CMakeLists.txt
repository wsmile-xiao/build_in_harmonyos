cmake_minimum_required(VERSION 3.15)
project(test_zita-alsa-pcmi LANGUAGES CXX)

find_package(zita-alsa-pcmi CONFIG REQUIRED)

add_executable(test_zita-alsa-pcmi test_zita_alsa_pcmi.cpp)
target_link_libraries(test_zita-alsa-pcmi PRIVATE zita-alsa-pcmi::zita-alsa-pcmi)
# zita-alsa-pcmi.h includes <alsa/asoundlib.h>; alsa-lib's published recipe
# does not export includedirs, so inject it here (set by the test conanfile).
target_include_directories(test_zita-alsa-pcmi PRIVATE ${ALSA_INCLUDE_DIR})
