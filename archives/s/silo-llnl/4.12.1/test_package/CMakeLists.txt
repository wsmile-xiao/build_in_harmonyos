cmake_minimum_required(VERSION 3.15)
project(test_silo_llnl C)

# Find silo-llnl via Conan CMakeDeps (dashes are normalized to underscores).
find_package(silo_llnl REQUIRED)

add_executable(test_silo_llnl test.c)
# Link purely through the Conan CMakeDeps target; it already carries the
# installed libsilo.a and include dirs. (A plain-signature link fallback is
# omitted: mixing keyword and plain target_link_libraries on the same target
# is a CMake error, and the target is the single source of truth.)
target_link_libraries(test_silo_llnl PRIVATE silo_llnl::silo_llnl)

enable_testing()
add_test(NAME test_silo_llnl COMMAND test_silo_llnl)
