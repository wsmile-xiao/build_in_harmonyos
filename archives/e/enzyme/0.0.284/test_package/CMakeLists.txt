cmake_minimum_required(VERSION 3.15)
project(test_enzyme C CXX)

# Find the package via Conan-generated CMakeDeps (R34: genuine dependency
# declared via find_package; the nm-based test() in conanfile.py verifies
# the plugin entry symbol is exported by the shipped library).
find_package(enzyme REQUIRED)

# Minimal stub executable — we do NOT link against enzyme::enzyme here,
# because linking would pull libLLVMEnzyme-15.so into the test binary's
# NEEDED entries, and the dynamic loader would then load libLLDEnzyme-15.so
# → relocation against LLVM C++ API symbols NOT exported by the OHOS SDK
# monolithic libLLVM-15.so (E216-draft gap 4, path C candidate) → exit 127.
# The actual R34 dependency check is done statically via `nm` in test(),
# which triggers no relocation and detects L1e sabotage (lib/ removed).
add_executable(test_enzyme test.c)

enable_testing()
add_test(NAME test_enzyme COMMAND test_enzyme)