cmake_minimum_required(VERSION 3.15)
project(test_kblocks C)

# Consumer test for kblocks 26.04.0 (R34 — must actually exercise the binary).
# The main test logic is in test.sh (POSIX sh, kfourinline 26.04.0 pattern)
# which calls the shipped kblocks binary with --version and --help.
# This CMakeLists.txt provides a minimal buildable target so the conan
# test_package machinery has something to compile; the real verification
# happens in test() via self.run("test.sh ...").

add_executable(test_kblocks test_kblocks.c)

enable_testing()
add_test(NAME test_kblocks COMMAND test_kblocks)
