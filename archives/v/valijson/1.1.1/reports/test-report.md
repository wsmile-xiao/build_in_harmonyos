# Test Report — valijson 1.1.1

## Build System
CMake (header-only INTERFACE library)

## Build Commands
```bash
cmake -S . -B build -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX
cmake --build build
cmake --install build --prefix $TEST_PREFIX
```

## Build Result
- Configure: SUCCESS
- Build: SUCCESS (header-only, no compilation needed)
- Install: SUCCESS (45 header files + 1 CMake config file)

## Staging Verification
- Install location: $TEST_PREFIX
- Header files: 45 .hpp files installed
- CMake config: valijsonConfig.cmake installed
- Total files: 46

## Smoke Test
A smoke test was performed using the installed headers with system jsoncpp:
- Compiled a test program that includes valijson headers
- Schema parsing: PASSED
- Document validation: PASSED
- maybeDouble() with strtod fix: PASSED (3.14 → true, not_a_number → false, 42 → true)

## Patches Applied
1. basic_adapter.hpp: Replaced std::from_chars for double with std::strtod
2. std_string_adapter.hpp: Replaced std::from_chars for double with std::strtod

## Notes
- valijson is a header-only C++ library, no binary artifacts produced
- Tests require git submodules (googletest, jsoncpp) which are not available
- Smoke test using system jsoncpp library verified header functionality
- The from_chars issue is tracked as knowledge graph draft E212
