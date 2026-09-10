cmake_minimum_required(VERSION 3.15)
project(test_ayatana-ido C)

# Consumer-link channel (PkgConfigDeps generates libayatana-ido3-0.4.pc plus
# all transitive dependency .pc files); pkg_check_modules propagates the
# transitive pango->harfbuzz (hb.h) and other include paths automatically.
find_package(PkgConfig REQUIRED)
pkg_check_modules(AYATANA_IDO REQUIRED IMPORTED_TARGET libayatana-ido3-0.4)

add_executable(test_ayatana-ido test.c)
target_link_libraries(test_ayatana-ido PkgConfig::AYATANA_IDO)

enable_testing()
add_test(NAME test_ayatana-ido COMMAND test_ayatana-ido)
