cmake_minimum_required(VERSION 3.15)
project(test_aliddns C)

# Test package: aliddns/po2lmo is an application package (the po2lmo CLI tool).
# test_aliddns.c re-implements the upstream sfh_hash to assert determinism.
# The real po2lmo invocation runs in conanfile.py test().

add_executable(test_aliddns test_aliddns.c)

enable_testing()
add_test(NAME test_aliddns COMMAND test_aliddns)
