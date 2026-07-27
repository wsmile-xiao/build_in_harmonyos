# Test Report — mongoose 7.21

## Build
- Build system: direct clang compilation (single-file amalgamated library)
- Compiler: clang 15.0.4
- Build command: `clang -O2 -fPIC -c mongoose.c -o mongoose.o && llvm-ar rcs libmongoose.a mongoose.o`
- Status: ✅ Passed

## Test Package
- Test binary: test_mongoose
- Test result: ✅ All tests passed
- Assertions:
  1. MG_VERSION == "7.21"
  2. mg_str("hello world").len == 11
  3. mg_match("hello world", "hello*") == true

## CI Simulation (W3)
- L0 (quality gate): ✅ pass
- L1 (test execution): ✅ pass
- L2 (smoke test): skip (library, no bin/)
- L4 (security scan): ✅ pass
- L5 (artifact baseline): ✅ pass
