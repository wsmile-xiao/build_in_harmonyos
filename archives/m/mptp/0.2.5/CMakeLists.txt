cmake_minimum_required(VERSION 3.15)
project(mptp VERSION 0.2.5 LANGUAGES C)
include(GNUInstallDirs)
# Release tarball includes the authoritative generated parsers/lexers.
# Compile every production source listed by src/Makefile.am; no algorithm stub.
add_executable(mptp
    src/arch.c src/auto.c src/aic.c src/mptp.c src/dp.c src/fasta.c
    src/likelihood.c src/maps.c src/multirun.c src/output.c src/random.c
    src/rtree.c src/svg.c src/svg_landscape.c src/util.c src/utree.c
    src/hash.c src/list.c src/parse_utree.c src/lex_utree.c
    src/parse_rtree.c src/lex_rtree.c)
target_compile_features(mptp PRIVATE c_std_99)
target_compile_definitions(mptp PRIVATE PACKAGE="mptp" PACKAGE_VERSION="${PROJECT_VERSION}")
target_include_directories(mptp PRIVATE src)
target_link_libraries(mptp PRIVATE m)
install(TARGETS mptp RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR})
install(FILES man/mptp.1 DESTINATION ${CMAKE_INSTALL_MANDIR}/man1)
install(FILES completion/mptp DESTINATION ${CMAKE_INSTALL_DATADIR}/bash-completion/completions OPTIONAL)
