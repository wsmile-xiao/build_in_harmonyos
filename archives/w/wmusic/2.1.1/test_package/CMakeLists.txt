cmake_minimum_required(VERSION 3.20)
project(wmusic_consumer LANGUAGES C)

# CMakeDeps-generated find_package for playerctl misses include dirs because
# the upstream recipe declares cpp_info without includedirs. Use pkg-config
# as the authoritative source — playerctl.pc ships correct -I/path/include/playerctl.
find_package(PkgConfig REQUIRED)
pkg_check_modules(PLAYERCTL REQUIRED IMPORTED_TARGET playerctl)

add_executable(wmusic_consumer test_wmusic_consumer.c)
target_link_libraries(wmusic_consumer PRIVATE PkgConfig::PLAYERCTL)
