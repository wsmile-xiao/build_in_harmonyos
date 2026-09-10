cmake_minimum_required(VERSION 3.15)
project(cbqn_test_package C)

find_package(cbqn REQUIRED CONFIG)

add_executable(test_cbqn test_cbqn.c)
target_link_libraries(test_cbqn PRIVATE cbqn::cbqn)

enable_testing()
add_test(NAME cbqn_ffi_consumer COMMAND test_cbqn)

# How the library is found at run time, and why nothing is hard-coded here:
# libcbqn.so carries a DT_SONAME, so the loader resolves it by bare name rather than by the path
# used at link time.  test_package/conanfile.py therefore runs ctest with env="conanrun", which
# exports LD_LIBRARY_PATH pointing at the package's lib directory.  Two alternatives were tried on
# the device and rejected: $<TARGET_FILE_DIR:cbqn::cbqn> fails at generate time
# ("Target \"cbqn::cbqn\" is not an executable or library") and reading
# IMPORTED_LOCATION_RELEASE off that imported target yields no value, so an ENVIRONMENT property
# built from it would silently never apply - worse than not having it.
#
# The dependency is real and observable: running the built binary with LD_LIBRARY_PATH removed
# exits 127 ("Error loading shared library libcbqn.so"), and CI's L1e gate additionally moves
# bin/, lib/ and include/ away and requires this test to fail.
