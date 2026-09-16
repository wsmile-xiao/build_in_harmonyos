cmake_minimum_required(VERSION 3.15)
project(pianobar_consumer LANGUAGES C)

find_package(pianobar CONFIG REQUIRED)
# Direct include in test_libpiano.c (<gcrypt.h>) plus indirect includes via
# <piano.h> ("../config.h" -> <libavfilter/version.h> and
# <libavformat/version.h>): link explicitly so the consumer TU resolves
# headers/libs even if transitive propagation changes.
find_package(libgcrypt CONFIG REQUIRED)
find_package(ffmpeg CONFIG REQUIRED)

add_executable(test_libpiano test_libpiano.c)
# Structural include (injected by CMakeToolchain cache in
# test_package/conanfile.py): absolute packaged include dir, independent
# of imported-target interface propagation.
target_include_directories(test_libpiano PRIVATE "${PIANOBAR_INCLUDE_DIR}")
target_link_libraries(test_libpiano PRIVATE pianobar::piano libgcrypt::libgcrypt ffmpeg::avformat ffmpeg::avfilter)
