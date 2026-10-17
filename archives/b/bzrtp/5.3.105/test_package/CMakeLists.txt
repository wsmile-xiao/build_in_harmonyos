cmake_minimum_required(VERSION 3.15)
project(test_bzrtp C)

# Consumer links the packaged library; transitive bctoolbox/sqlite3
# include dirs and link libraries arrive via the generated CMakeDeps.
# Explicit finds (2026-09-18 round: test_package failed at
# 'bctoolbox/list.h file not found' via bzrtp/bzrtp.h -> vendored
# bctoolbox/crypto.h): the packaged bzrtp/bzrtp.h unconditionally includes
# bctoolbox/crypto.h, whose line 22 needs bctoolbox/list.h from the
# bctoolbox package include dir. Relying on bzrtp::bzrtp alone left that
# -I off the compile line on真机, so find/link the two Conan-provided
# deps explicitly (their CMakeDeps configs are generated transitively;
# lowercase names are the test_package-side defaults, no set_property here).
find_package(bzrtp REQUIRED)
find_package(bctoolbox REQUIRED)
find_package(sqlite3 REQUIRED)

add_executable(test_bzrtp test_bzrtp.c)
target_link_libraries(test_bzrtp PRIVATE bzrtp::bzrtp bctoolbox::bctoolbox sqlite3::sqlite3)

enable_testing()
add_test(NAME test_bzrtp COMMAND test_bzrtp)
