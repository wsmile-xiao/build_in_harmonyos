# Test Report — jitterentropy-library 3.6.3

## Test Method
Conan test_package with CMake, running test_jitterentropy binary.

## Test Results
- **conan create**: PASS
- **test_package build**: PASS
- **test_package run**: PASS
- **L0 quality gate**: PASS
- **W3 local CI simulation**: PASS

## Test Description
The test program initializes the jitterentropy library, allocates an entropy collector,
reads 32 bytes of random entropy, and verifies the return value matches the requested size.

## Assertion Count
4 assertions:
1. jent_entropy_init() returns 0
2. jent_entropy_collector_alloc() returns non-NULL
3. jent_read_entropy() returns sizeof(buffer)
4. jent_entropy_collector_free() succeeds
