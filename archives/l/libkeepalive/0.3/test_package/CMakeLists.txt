cmake_minimum_required(VERSION 3.15)
project(test_libkeepalive C)

# libkeepalive is an LD_PRELOAD interposer, so it is deliberately *not* linked
# into the consumer: linking it would make the interposition unconditional and
# would prevent the "library is inactive unless preloaded" baseline from being
# tested. The consumer is exercised through LD_PRELOAD in conanfile.py test().
add_executable(test_libkeepalive test.c)
